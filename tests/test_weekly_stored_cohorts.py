import json
from datetime import timedelta

import pytest

from investment_terminal.cli.weekly_stored_cohorts import main
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.operations.weekly_stored_cohorts import measure_weekly_stored_cohorts
from investment_terminal.repositories.candle_repository import CandleRepository
from tests.test_weekly_candle_refresh import END, candle, plan_and_sources
from tests.test_weekly_stored_coverage import _checkpoint


def _bins(items):
    return {item["bucket"]: item["count"] for item in items}


def test_cohorts_are_exclusive_redacted_and_read_only(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    start = END - timedelta(days=400)
    path = tmp_path / "candles.db"
    database = Database(path)
    database.initialize()
    repository = CandleRepository(database)
    first, second = (item[0] for item in plan.items)
    for day in (1, 399):
        repository.save(candle(first, start + timedelta(days=day)))
    for day in (80, 82):
        repository.save(candle(second, start + timedelta(days=day)))
    checkpoint = _checkpoint(plan)
    checkpoint["outcomes"][second] = {
        "status": "FAILED", "category": "RESPONSE_NUMERIC",
        "downloaded": 0, "inserted": 0, "duplicates": 0,
        "omitted_trailing_count": 0, "stored_count": 0,
    }
    before = path.read_bytes()
    result = measure_weekly_stored_cohorts(
        plan, checkpoint, database.connection, history_start=start,
    )
    assert result["schema_version"] == 1
    assert result["operation_identity"] == "WEEKLY_STORED_COHORTS"
    assert _bins(result["first_observation_age_bins"]) == {
        "WITHIN_7_DAYS": 1, "OVER_7_TO_30_DAYS": 0,
        "OVER_30_TO_365_DAYS": 1, "AFTER_365_DAYS": 0, "NO_ROWS": 0,
    }
    assert _bins(result["endpoint_proxy_bins"]) == {
        "BOTH": 1, "START_ONLY": 0, "END_ONLY": 0, "NEITHER": 1,
    }
    assert _bins(result["largest_observed_gap_bins"]) == {
        "NO_GAP_OVER_7_DAYS": 1, "GAP_OVER_7_TO_30_DAYS": 0,
        "GAP_OVER_30_DAYS": 1,
    }
    intersections = {
        item["category"]: item for item in result["weekly_outcome_intersections"]
    }
    assert intersections["SUCCESS"]["gap_over_7_days_count"] == 1
    assert intersections["RESPONSE_NUMERIC"]["missing_start_proxy_count"] == 1
    assert all(symbol not in str(result) for symbol, _ in plan.items)
    database.close()
    assert path.read_bytes() == before


def test_empty_window_and_invalid_evidence_fail_closed(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    database = Database(tmp_path / "candles.db")
    database.initialize()
    start = END - timedelta(days=40)
    empty = measure_weekly_stored_cohorts(
        plan, _checkpoint(plan), database.connection, history_start=start,
    )
    assert _bins(empty["first_observation_age_bins"])["NO_ROWS"] == 2
    assert _bins(empty["endpoint_proxy_bins"])["NEITHER"] == 2
    with pytest.raises(ValueError, match="history_start"):
        measure_weekly_stored_cohorts(
            plan, _checkpoint(plan), database.connection, history_start=None,
        )
    with pytest.raises(ValueError, match="Complete weekly checkpoint"):
        measure_weekly_stored_cohorts(
            plan, _checkpoint(plan, incomplete=True), database.connection,
            history_start=start,
        )
    repository = CandleRepository(database)
    repository.save(candle(plan.items[0][0], start + timedelta(days=1)))
    database.connection.execute(
        "UPDATE candles SET timestamp = 'invalid' WHERE symbol = ?",
        (plan.items[0][0],),
    )
    database.connection.commit()
    with pytest.raises(ValueError, match="invalid timestamps"):
        measure_weekly_stored_cohorts(
            plan, _checkpoint(plan), database.connection, history_start=start,
        )
    database.close()


@pytest.mark.parametrize("first_day,expected_age", [
    (7, "WITHIN_7_DAYS"),
    (8, "OVER_7_TO_30_DAYS"),
    (30, "OVER_7_TO_30_DAYS"),
    (31, "OVER_30_TO_365_DAYS"),
    (365, "OVER_30_TO_365_DAYS"),
    (366, "AFTER_365_DAYS"),
])
def test_first_observation_boundaries(tmp_path, first_day, expected_age):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    start = END - timedelta(days=400)
    database = Database(tmp_path / "candles.db")
    database.initialize()
    CandleRepository(database).save(
        candle(plan.items[0][0], start + timedelta(days=first_day))
    )
    report = measure_weekly_stored_cohorts(
        plan, _checkpoint(plan), database.connection, history_start=start,
    )
    assert _bins(report["first_observation_age_bins"])[expected_age] == 1
    database.close()


def test_midrange_gap_and_end_only_proxy(tmp_path):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, sources.get, end=END)
    start = END - timedelta(days=40)
    database = Database(tmp_path / "candles.db")
    database.initialize()
    repository = CandleRepository(database)
    for day in (10, 39):
        repository.save(candle(plan.items[0][0], start + timedelta(days=day)))
    report = measure_weekly_stored_cohorts(
        plan, _checkpoint(plan), database.connection, history_start=start,
    )
    assert _bins(report["endpoint_proxy_bins"])["END_ONLY"] == 1
    assert _bins(report["largest_observed_gap_bins"])["GAP_OVER_7_TO_30_DAYS"] == 1
    database.close()


def test_cli_versioned_report_and_failure_are_redacted(tmp_path):
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
    report = tmp_path / "cohorts.json"
    assert main(args + [
        "--history-start", start, "--report-output", str(report),
    ]) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["selected_series_count"] == 2
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        main(args + [
            "--history-start", start, "--report-output", str(report),
        ])
    failed_path = tmp_path / "failed.json"
    assert main(args + [
        "--history-start", "bad-private-value", "--report-output", str(failed_path),
    ]) == 1
    failed = json.loads(failed_path.read_text(encoding="utf-8"))
    assert failed["status"] == "FAILED"
    assert failed["history_start"] is None
    assert "bad-private-value" not in str(failed)
