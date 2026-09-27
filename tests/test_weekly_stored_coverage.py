import json
from datetime import timedelta

import pytest

from investment_terminal.cli.weekly_stored_coverage import main
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.operations.weekly_stored_coverage import measure_weekly_stored_coverage
from investment_terminal.repositories.candle_repository import CandleRepository
from tests.test_weekly_candle_refresh import END, LAST, candle, plan_and_sources


def _checkpoint(plan, *, incomplete=False):
    outcomes = {
        symbol: {
            "status": "SUCCESS", "category": None, "downloaded": 1,
            "inserted": 1, "duplicates": 0, "omitted_trailing_count": 0,
            "stored_count": 1,
        }
        for symbol, _ in plan.items[:1 if incomplete else None]
    }
    return {
        "schema_version": 1, "operation_identity": "WEEKLY_CANDLE_REFRESH",
        "manifest_checksum": plan.manifest_checksum, "end": plan.end.isoformat(),
        "selection_checksum": plan.selection_checksum, "outcomes": outcomes,
    }


def test_aggregate_is_read_only_and_redacted(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    path = tmp_path / "candles.db"
    database = Database(path)
    database.initialize()
    repository = CandleRepository(database)
    repository.save(candle(plan.items[0][0], LAST))
    repository.save(candle(plan.items[1][0], LAST))
    checkpoint = _checkpoint(plan)
    before = path.read_bytes()
    result = measure_weekly_stored_coverage(plan, checkpoint, database.connection)
    assert result["status"] == "COMPLETE"
    assert result["coverage"]["selected_series_count"] == 2
    assert result["coverage"]["stored_row_count_before_end"] == 2
    assert result["coverage"]["one_to_49_count"] == 2
    assert result["coverage"]["sample_50_ready_count"] == 0
    assert result["coverage"]["last_candle_within_7_calendar_days_count"] == 2
    assert all(symbol not in str(result) for symbol, _ in plan.items)
    database.close()
    assert path.read_bytes() == before


def test_cli_rejects_incomplete_checkpoint_and_missing_database(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    for index, source in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(json.dumps(source), encoding="utf-8")
    checkpoint_path = tmp_path / "weekly.json"
    checkpoint_path.write_text(json.dumps(_checkpoint(plan, incomplete=True)), encoding="utf-8")
    database_path = tmp_path / "missing.db"
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_dir),
        "--weekly-checkpoint", str(checkpoint_path),
        "--database", str(database_path),
    ]
    missing_report = tmp_path / "missing-report.json"
    assert main(args + ["--report-output", str(missing_report)]) == 1
    assert not database_path.exists()
    assert json.loads(missing_report.read_text(encoding="utf-8"))["coverage"] is None
    database = Database(database_path)
    database.initialize()
    database.close()
    incomplete_report = tmp_path / "incomplete-report.json"
    assert main(args + ["--report-output", str(incomplete_report)]) == 1
    assert json.loads(incomplete_report.read_text(encoding="utf-8"))["status"] == "FAILED"


def test_cli_complete_checkpoint_and_bad_binding(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    for index, source in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(json.dumps(source), encoding="utf-8")
    checkpoint_path = tmp_path / "weekly.json"
    checkpoint = _checkpoint(plan)
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    database_path = tmp_path / "candles.db"
    database = Database(database_path)
    database.initialize()
    CandleRepository(database).save(candle(plan.items[0][0], LAST))
    database.close()
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_dir),
        "--weekly-checkpoint", str(checkpoint_path),
        "--database", str(database_path),
    ]
    report = tmp_path / "report.json"
    assert main(args + ["--report-output", str(report)]) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["coverage"]["zero_count"] == 1
    checkpoint["selection_checksum"] = "0" * 64
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    bad_report = tmp_path / "bad-report.json"
    assert main(args + ["--report-output", str(bad_report)]) == 1
    assert json.loads(bad_report.read_text(encoding="utf-8"))["status"] == "FAILED"


def test_sample_bins_and_exclusive_end(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    database = Database(tmp_path / "candles.db")
    database.initialize()
    repository = CandleRepository(database)
    for index in range(200):
        repository.save(candle(plan.items[0][0], LAST - timedelta(days=index)))
    repository.save(candle(plan.items[0][0], END))
    for index in range(50):
        repository.save(candle(plan.items[1][0], LAST - timedelta(days=index)))
    result = measure_weekly_stored_coverage(plan, _checkpoint(plan), database.connection)
    coverage = result["coverage"]
    assert coverage["stored_row_count_before_end"] == 250
    assert coverage["row_count_at_or_after_end"] == 1
    assert coverage["sample_50_ready_count"] == 2
    assert coverage["sample_200_ready_count"] == 1
    database.close()


@pytest.mark.parametrize("field,value", [
    ("timestamp", "not-a-date"), ("currency", "EUR"),
])
def test_invalid_stored_data_fails_closed(tmp_path, field, value):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    database = Database(tmp_path / "candles.db")
    database.initialize()
    CandleRepository(database).save(candle(plan.items[0][0], LAST))
    database.connection.execute(
        f"UPDATE candles SET {field} = ? WHERE symbol = ?",
        (value, plan.items[0][0]),
    )
    database.connection.commit()
    with pytest.raises(ValueError, match="invalid timestamps or currency"):
        measure_weekly_stored_coverage(plan, _checkpoint(plan), database.connection)
    database.close()
