import json
from datetime import timedelta

import pytest

from investment_terminal.cli.weekly_stale_gap_diagnostic import main
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.operations.weekly_stale_gap_diagnostic import (
    measure_weekly_stale_gap_diagnostic,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from tests.test_weekly_candle_refresh import END, candle, plan_and_sources
from tests.test_weekly_stored_coverage import _checkpoint


def _bins(items):
    return {item["bucket"]: item["count"] for item in items}


def _groups(items):
    return {item["group"]: item for item in items}


def test_stale_and_gap_only_groups_are_redacted_and_read_only(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    start = END - timedelta(days=40)
    path = tmp_path / "candles.db"
    database = Database(path)
    database.initialize()
    repository = CandleRepository(database)
    stale_symbol, gap_symbol = (item[0] for item in plan.items)
    for day in (20, 21):
        repository.save(candle(stale_symbol, start + timedelta(days=day)))
    for day in (1, 39):
        repository.save(candle(gap_symbol, start + timedelta(days=day)))
    checkpoint = _checkpoint(plan)
    checkpoint["outcomes"][stale_symbol] = {
        "status": "SUCCESS", "category": None, "downloaded": 2,
        "inserted": 0, "duplicates": 2, "omitted_trailing_count": 1,
        "stored_count": 2,
    }
    before = path.read_bytes()
    report = measure_weekly_stale_gap_diagnostic(
        plan, checkpoint, database.connection, history_start=start,
    )
    assert report["status"] == "COMPLETE"
    assert report["stale_success_count"] == 1
    assert report["long_gap_success_count"] == 1
    assert report["intersection_count"] == 0
    assert report["union_count"] == 2
    assert _bins(report["staleness_bins"])["OVER_14_TO_30_DAYS"] == 1
    assert _bins(report["largest_gap_bins"])["OVER_30_TO_90_DAYS"] == 1
    groups = _groups(report["disjoint_groups"])
    assert groups["STALE_ONLY"]["downloaded_total"] == 2
    assert groups["STALE_ONLY"]["inserted_total"] == 0
    assert groups["STALE_ONLY"]["duplicate_total"] == 2
    assert groups["STALE_ONLY"]["omitted_trailing_total"] == 1
    assert groups["GAP_ONLY"]["series_count"] == 1
    assert groups["BOTH"]["series_count"] == 0
    assert all(symbol not in str(report) for symbol, _ in plan.items)
    database.close()
    assert path.read_bytes() == before


def test_overlap_is_counted_once_and_failed_series_are_excluded(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    start = END - timedelta(days=40)
    database = Database(tmp_path / "candles.db")
    database.initialize()
    repository = CandleRepository(database)
    first, second = (item[0] for item in plan.items)
    for symbol in (first, second):
        for day in (1, 20):
            repository.save(candle(symbol, start + timedelta(days=day)))
    checkpoint = _checkpoint(plan)
    checkpoint["outcomes"][second] = {
        "status": "FAILED", "category": "RESPONSE_NUMERIC",
        "downloaded": 0, "inserted": 0, "duplicates": 0,
        "omitted_trailing_count": 0, "stored_count": 0,
    }
    report = measure_weekly_stale_gap_diagnostic(
        plan, checkpoint, database.connection, history_start=start,
    )
    assert report["stale_success_count"] == 1
    assert report["long_gap_success_count"] == 1
    assert report["intersection_count"] == 1
    assert report["union_count"] == 1
    assert _groups(report["disjoint_groups"])["BOTH"]["series_count"] == 1
    database.close()


def test_no_window_rows_and_invalid_inputs_fail_closed(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    start = END - timedelta(days=40)
    database = Database(tmp_path / "candles.db")
    database.initialize()
    CandleRepository(database).save(candle(plan.items[0][0], start - timedelta(days=1)))
    report = measure_weekly_stale_gap_diagnostic(
        plan, _checkpoint(plan), database.connection, history_start=start,
    )
    assert report["stale_success_count"] == 2
    assert _bins(report["staleness_bins"])["NO_WINDOW_ROWS"] == 2
    with pytest.raises(ValueError, match="history_start"):
        measure_weekly_stale_gap_diagnostic(
            plan, _checkpoint(plan), database.connection, history_start=None,
        )
    with pytest.raises(ValueError, match="Complete weekly checkpoint"):
        measure_weekly_stale_gap_diagnostic(
            plan, _checkpoint(plan, incomplete=True), database.connection,
            history_start=start,
        )
    database.connection.execute(
        "UPDATE candles SET currency = 'EUR' WHERE symbol = ?",
        (plan.items[0][0],),
    )
    database.connection.commit()
    with pytest.raises(ValueError, match="invalid timestamps or currency"):
        measure_weekly_stale_gap_diagnostic(
            plan, _checkpoint(plan), database.connection, history_start=start,
        )
    database.close()


def test_cli_writes_versioned_redacted_success_and_failure(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    for index, source in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(
            json.dumps(source), encoding="utf-8"
        )
    checkpoint_path = tmp_path / "weekly.json"
    checkpoint_path.write_text(json.dumps(_checkpoint(plan)), encoding="utf-8")
    database_path = tmp_path / "candles.db"
    database = Database(database_path)
    database.initialize()
    database.close()
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_dir),
        "--weekly-checkpoint", str(checkpoint_path),
        "--database", str(database_path),
    ]
    start = (END - timedelta(days=40)).isoformat()
    report_path = tmp_path / "report.json"
    assert main(args + [
        "--history-start", start, "--report-output", str(report_path),
    ]) == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["union_count"] == 2
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        main(args + [
            "--history-start", start, "--report-output", str(report_path),
        ])
    failed_path = tmp_path / "failed.json"
    assert main(args + [
        "--history-start", "private-bad-value", "--report-output", str(failed_path),
    ]) == 1
    failed = json.loads(failed_path.read_text(encoding="utf-8"))
    assert failed["status"] == "FAILED"
    assert failed["union_count"] is None
    assert "private-bad-value" not in str(failed)
    mismatched = _checkpoint(plan)
    mismatched["selection_checksum"] = "0" * 64
    checkpoint_path.write_text(json.dumps(mismatched), encoding="utf-8")
    binding_path = tmp_path / "bad-binding.json"
    assert main(args + [
        "--history-start", start, "--report-output", str(binding_path),
    ]) == 1
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    assert binding["status"] == "FAILED"
    assert binding["selection_checksum"] is None
