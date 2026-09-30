import json
from datetime import timedelta

import pytest

from investment_terminal.cli.latest_raw_indicator_projection import main
from investment_terminal.database.database import Database
from investment_terminal.indicators.technical_indicators import TechnicalIndicators
from investment_terminal.operations.latest_raw_indicator_projection import (
    project_latest_raw_indicators,
)
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_weekly_candle_refresh import END, candle, plan_and_sources
from tests.test_weekly_stored_coverage import _checkpoint


def _fixture(tmp_path, count, *, final_offset=1):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(
        manifest, checksum, sources.get, end=END,
    )
    database = Database(tmp_path / "candles.db")
    database.initialize()
    symbol = plan.items[0][0]
    candles = [
        candle(symbol, END - timedelta(days=final_offset + index))
        for index in range(count - 1, -1, -1)
    ]
    CandleRepository(database).save_many(candles)
    return manifest, checksum, sources, plan, database, candles


@pytest.mark.parametrize("count,category", [
    (0, "NO_CANDLES"), (49, "UNDER_50"), (50, "50_TO_199"),
    (199, "50_TO_199"), (200, "BOTH_AVAILABLE"),
])
def test_sma_boundaries_match_existing_indicator(tmp_path, count, category):
    _, _, _, plan, database, candles = _fixture(tmp_path, count)
    before = (tmp_path / "candles.db").read_bytes()
    private, report = project_latest_raw_indicators(
        plan, _checkpoint(plan), database.connection, max_items=1,
    )
    item = private["items"][0]
    assert item["availability"] == category
    assert item["sample_count_capped_at_200"] == count
    assert item["sma50_raw_close"] == (
        TechnicalIndicators.sma(candles, 50)[-1] if count >= 50 else None
    )
    assert item["sma200_raw_close"] == (
        TechnicalIndicators.sma(candles, 200)[-1] if count >= 200 else None
    )
    assert item["recent_7_calendar_day_proxy"] is (count > 0)
    assert report["price_basis"] == "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT"
    assert report["sma50_available_count"] == (count >= 50)
    assert report["sma200_available_count"] == (count >= 200)
    assert symbol_not_in_report(plan, report)
    database.close()
    assert (tmp_path / "candles.db").read_bytes() == before


def symbol_not_in_report(plan, report):
    return all(symbol not in str(report) for symbol, _ in plan.items)


def test_stale_sample_and_exclusive_end(tmp_path):
    _, _, _, plan, database, _ = _fixture(tmp_path, 200, final_offset=101)
    symbol = plan.items[0][0]
    CandleRepository(database).save(candle(symbol, END))
    private, report = project_latest_raw_indicators(
        plan, _checkpoint(plan), database.connection, max_items=1,
    )
    item = private["items"][0]
    assert item["availability"] == "BOTH_AVAILABLE"
    assert item["latest_timestamp"] == (END - timedelta(days=101)).isoformat()
    assert item["recent_7_calendar_day_proxy"] is False
    assert report["recent_7_calendar_day_proxy_count"] == 0
    database.close()


@pytest.mark.parametrize("field,value,match", [
    ("close_price", "bad", "close price"),
    ("close_price", -1, "close price"),
    ("currency", "EUR", "timestamps or currency"),
    ("timestamp", "invalid", "timestamps or currency"),
])
def test_invalid_stored_evidence_fails_closed(tmp_path, field, value, match):
    _, _, _, plan, database, _ = _fixture(tmp_path, 1)
    symbol = plan.items[0][0]
    database.connection.execute(
        f"UPDATE candles SET {field} = ? WHERE symbol = ?", (value, symbol),
    )
    database.connection.commit()
    with pytest.raises(ValueError, match=match):
        project_latest_raw_indicators(
            plan, _checkpoint(plan), database.connection, max_items=1,
        )
    database.close()


def test_incomplete_and_mismatched_checkpoint_fail_closed(tmp_path):
    _, _, _, plan, database, _ = _fixture(tmp_path, 1)
    with pytest.raises(ValueError, match="Complete weekly checkpoint"):
        project_latest_raw_indicators(
            plan, _checkpoint(plan, incomplete=True), database.connection,
            max_items=1,
        )
    checkpoint = _checkpoint(plan)
    checkpoint["selection_checksum"] = "0" * 64
    with pytest.raises(ValueError, match="binding"):
        project_latest_raw_indicators(
            plan, checkpoint, database.connection, max_items=1,
        )
    with pytest.raises(ValueError, match="max_items"):
        project_latest_raw_indicators(
            plan, _checkpoint(plan), database.connection, max_items=0,
        )
    database.close()


def _cli_args(tmp_path, count=50):
    manifest, checksum, sources, plan, database, _ = _fixture(tmp_path, count)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for index, source in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(
            json.dumps(source), encoding="utf-8",
        )
    checkpoint_path = tmp_path / "weekly.json"
    checkpoint_path.write_text(json.dumps(_checkpoint(plan)), encoding="utf-8")
    private_path = tmp_path / "private.json"
    report_path = tmp_path / "report.json"
    database.close()
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_dir),
        "--weekly-checkpoint", str(checkpoint_path),
        "--database", str(tmp_path / "candles.db"),
        "--end", END.isoformat(), "--max-items", "1",
        "--private-output", str(private_path),
        "--report-output", str(report_path),
    ]
    return plan, args, private_path, report_path


def test_cli_writes_private_values_and_redacted_report(tmp_path):
    plan, args, private_path, report_path = _cli_args(tmp_path)
    assert main(args) == 0
    private = json.loads(private_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert private["status"] == report["status"] == "COMPLETE"
    assert private["items"][0]["symbol"] == plan.items[0][0]
    assert report["availability_counts"][2]["count"] == 1
    assert symbol_not_in_report(plan, report)
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        main(args)


def test_cli_report_write_failure_removes_private_output(tmp_path):
    _, args, private_path, report_path = _cli_args(tmp_path)
    calls = 0

    def fail_success_report(path, payload):
        nonlocal calls
        calls += 1
        if path == report_path and payload["status"] == "COMPLETE":
            raise OSError("private report write failure")
        return write_json_atomic(path, payload)

    assert main(args, writer=fail_success_report) == 1
    assert calls == 3
    assert not private_path.exists()
    failed = json.loads(report_path.read_text(encoding="utf-8"))
    assert failed["status"] == "FAILED"
    assert "private report write failure" not in str(failed)


def test_cli_private_write_failure_removes_partial_output(tmp_path):
    _, args, private_path, report_path = _cli_args(tmp_path)

    def fail_private_after_write(path, payload):
        write_json_atomic(path, payload)
        if path == private_path:
            raise OSError("private output write failure")

    assert main(args, writer=fail_private_after_write) == 1
    assert not private_path.exists()
    failed = json.loads(report_path.read_text(encoding="utf-8"))
    assert failed["status"] == "FAILED"
    assert "private output write failure" not in str(failed)


def test_cli_bad_checkpoint_leaves_only_redacted_failed_report(tmp_path):
    plan, args, private_path, report_path = _cli_args(tmp_path)
    checkpoint_path = tmp_path / "weekly.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["selection_checksum"] = "0" * 64
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    assert main(args) == 1
    assert not private_path.exists()
    failed = json.loads(report_path.read_text(encoding="utf-8"))
    assert failed["status"] == "FAILED"
    assert symbol_not_in_report(plan, failed)


def test_cli_rejects_output_inside_source_evidence_without_writing(tmp_path):
    _, args, private_path, report_path = _cli_args(tmp_path)
    unsafe_report = tmp_path / "source" / "new-report.json"
    args[args.index(str(report_path))] = str(unsafe_report)
    with pytest.raises(SystemExit, match="paths are invalid"):
        main(args)
    assert not private_path.exists()
    assert not unsafe_report.exists()
