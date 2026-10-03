import json
from datetime import timedelta
from hashlib import sha256

import pytest

from investment_terminal.cli.instrument_research_export import main
from investment_terminal.database.database import Database
from investment_terminal.operations.instrument_research_export import (
    build_instrument_research_export,
)
from investment_terminal.operations.latest_raw_indicator_projection import (
    project_latest_raw_indicators,
)
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_weekly_candle_refresh import END, candle, plan_and_sources
from tests.test_weekly_stored_coverage import _checkpoint


def _fixture(tmp_path, *, count=200):
    manifest, checksum, sources = plan_and_sources()
    plan = WeeklyCandleRefreshPlan.from_manifest(
        manifest, checksum, sources.get, end=END,
    )
    database_path = tmp_path / "candles.db"
    database = Database(database_path)
    database.initialize()
    symbol = plan.items[0][0]
    CandleRepository(database).save_many([
        candle(symbol, END - timedelta(days=offset))
        for offset in range(count, 0, -1)
    ])
    checkpoint = _checkpoint(plan)
    projection, _ = project_latest_raw_indicators(
        plan, checkpoint, database.connection, max_items=len(plan.items),
    )
    projection_path = tmp_path / "projection.json"
    write_json_atomic(projection_path, projection)
    projection_hash = sha256(projection_path.read_bytes()).hexdigest()
    return (
        manifest, checksum, sources, plan, database, checkpoint,
        projection, projection_path, projection_hash,
    )


def _export(fixture, *, history_start=None, symbol=None):
    _, _, _, plan, database, checkpoint, projection, _, digest = fixture
    return build_instrument_research_export(
        plan, checkpoint, projection, digest, database.connection,
        symbol=symbol or plan.items[0][0],
        history_start=history_start or END - timedelta(days=30),
    )


def test_single_instrument_export_is_ordered_private_and_read_only(tmp_path):
    fixture = _fixture(tmp_path)
    _, _, _, plan, database, _, _, _, digest = fixture
    database.close()
    before = (tmp_path / "candles.db").read_bytes()
    database = Database(tmp_path / "candles.db")
    fixture = (*fixture[:4], database, *fixture[5:])
    private, report = _export(fixture)
    symbol = plan.items[0][0]
    assert private["operation_identity"] == "INSTRUMENT_RESEARCH_EXPORT"
    assert private["symbol"] == symbol
    assert private["source_projection_sha256"] == digest
    assert private["candle_count"] == report["candle_count"] == 30
    assert private["history_candles_sha256"] == report["history_candles_sha256"]
    assert [item["timestamp"] for item in private["candles"]] == [
        (END - timedelta(days=offset)).isoformat() for offset in range(30, 0, -1)
    ]
    assert private["indicator"]["sma200_raw_close"] == 10.0
    assert report["availability"] == "BOTH_AVAILABLE"
    assert report["recent_7_calendar_day_proxy"] is True
    assert symbol not in str(report)
    assert "candles" not in report and "currency" not in report
    database.close()
    assert (tmp_path / "candles.db").read_bytes() == before


def test_empty_selected_history_is_explicit(tmp_path):
    fixture = _fixture(tmp_path, count=0)
    private, report = _export(fixture)
    assert private["candles"] == []
    assert private["indicator"]["sma50_raw_close"] is None
    assert report["candle_count"] == 0
    assert report["availability"] == "NO_CANDLES"
    fixture[4].close()


def test_export_refuses_more_than_4000_stored_rows(tmp_path):
    fixture = _fixture(tmp_path, count=0)
    _, _, _, plan, database, checkpoint, _, _, digest = fixture
    symbol = plan.items[0][0]
    database.connection.executemany(
        """INSERT INTO candles (symbol, resolution, timestamp, open_price,
           high_price, low_price, close_price, volume, currency)
           VALUES (?, 'D', ?, 10, 11, 9, 10, 100, 'USD')""",
        [
            (symbol, (END - timedelta(hours=offset)).isoformat())
            for offset in range(4001, 0, -1)
        ],
    )
    database.connection.commit()
    projection, _ = project_latest_raw_indicators(
        plan, checkpoint, database.connection, max_items=len(plan.items),
    )
    with pytest.raises(ValueError, match="candle bound"):
        build_instrument_research_export(
            plan, checkpoint, projection, digest, database.connection,
            symbol=symbol, history_start=END - timedelta(days=200),
        )
    database.close()


@pytest.mark.parametrize("change,match", [
    ("symbol", "not in the selected"),
    ("checksum", "checksum"),
    ("selection", "selection"),
    ("end", "binding"),
    ("checkpoint", "checkpoint"),
    ("window", "bounded UTC window"),
])
def test_export_rejects_unbound_or_unbounded_inputs(tmp_path, change, match):
    fixture = _fixture(tmp_path, count=2)
    _, _, _, plan, database, checkpoint, projection, _, digest = fixture
    if change == "symbol":
        symbol = "NOT-SELECTED"
    else:
        symbol = plan.items[0][0]
    if change == "checksum":
        digest = "bad"
    elif change == "selection":
        projection["items"][0]["symbol"] = "WRONG"
    elif change == "end":
        projection["end"] = END.isoformat().replace("2026", "2025")
    elif change == "checkpoint":
        checkpoint["selection_checksum"] = "0" * 64
    start = END - timedelta(days=3661 if change == "window" else 30)
    with pytest.raises(ValueError, match=match):
        build_instrument_research_export(
            plan, checkpoint, projection, digest, database.connection,
            symbol=symbol, history_start=start,
        )
    database.close()


@pytest.mark.parametrize("field,value,match", [
    ("close_price", 10.5, "no longer matches"),
    ("high_price", 5.0, "invalid OHLC"),
    ("currency", "EUR", "timestamp or currency"),
    ("timestamp", "invalid", "timestamp or currency"),
])
def test_export_rejects_changed_or_invalid_stored_rows(tmp_path, field, value, match):
    fixture = _fixture(tmp_path, count=2)
    _, _, _, plan, database, _, _, _, _ = fixture
    symbol = plan.items[0][0]
    database.connection.execute(
        f"UPDATE candles SET {field} = ? WHERE symbol = ? AND timestamp = ?",
        (value, symbol, (END - timedelta(days=1)).isoformat()),
    )
    database.connection.commit()
    with pytest.raises(ValueError, match=match):
        _export(fixture)
    database.close()


def _cli_args(tmp_path):
    fixture = _fixture(tmp_path, count=2)
    manifest, checksum, sources, plan, database, checkpoint, _, projection_path, digest = fixture
    database.close()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for index, value in sources.items():
        (source_dir / f"batch_{index:04d}.json").write_text(
            json.dumps(value), encoding="utf-8",
        )
    checkpoint_path = tmp_path / "weekly.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    private_path = tmp_path / "private.json"
    report_path = tmp_path / "report.json"
    args = [
        "--manifest", str(manifest_path), "--manifest-checksum", checksum,
        "--source-checkpoint-directory", str(source_dir),
        "--weekly-checkpoint", str(checkpoint_path),
        "--projection", str(projection_path),
        "--projection-sha256", digest,
        "--database", str(tmp_path / "candles.db"),
        "--symbol", plan.items[0][0],
        "--history-start", (END - timedelta(days=30)).isoformat(),
        "--end", END.isoformat(),
        "--private-output", str(private_path),
        "--report-output", str(report_path),
    ]
    return args, private_path, report_path, projection_path


def test_cli_writes_separate_private_and_redacted_results(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)
    before = (tmp_path / "candles.db").read_bytes()
    assert main(args) == 0
    private = json.loads(private_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert private["status"] == report["status"] == "COMPLETE"
    assert private["symbol"] not in str(report)
    assert report["candle_count"] == 2
    assert (tmp_path / "candles.db").read_bytes() == before
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        main(args)


def test_cli_checksum_mismatch_leaves_only_generic_report(tmp_path):
    args, private_path, report_path, projection_path = _cli_args(tmp_path)
    projection_path.write_text("{}", encoding="utf-8")
    assert main(args) == 1
    assert not private_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "FAILED"
    assert "symbol" not in str(report)


def test_cli_report_write_failure_removes_private_result(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)

    def fail_success_report(path, payload):
        if path == report_path and payload["status"] == "COMPLETE":
            raise OSError("private write error")
        return write_json_atomic(path, payload)

    assert main(args, writer=fail_success_report) == 1
    assert not private_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "FAILED"
    assert "private write error" not in str(report)


def test_cli_private_write_failure_removes_partial_result(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)

    def fail_private_after_write(path, payload):
        write_json_atomic(path, payload)
        if path == private_path:
            raise OSError("private data failure")

    assert main(args, writer=fail_private_after_write) == 1
    assert not private_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "FAILED"
    assert "private data failure" not in str(report)


def test_cli_rejects_output_alias_before_writing(tmp_path):
    args, private_path, report_path, projection_path = _cli_args(tmp_path)
    args[args.index(str(private_path))] = str(projection_path)
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        main(args)
    assert not report_path.exists()


def test_cli_rejects_same_two_outputs_before_writing(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)
    args[args.index(str(report_path))] = str(private_path)
    with pytest.raises(SystemExit, match="paths are invalid"):
        main(args)
    assert not private_path.exists()


def test_cli_rejects_output_inside_source_directory(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)
    unsafe_report = tmp_path / "source" / "report.json"
    args[args.index(str(report_path))] = str(unsafe_report)
    with pytest.raises(SystemExit, match="paths are invalid"):
        main(args)
    assert not private_path.exists() and not unsafe_report.exists()


def test_cli_missing_database_does_not_create_it(tmp_path):
    args, private_path, report_path, _ = _cli_args(tmp_path)
    database_path = tmp_path / "missing.db"
    args[args.index(str(tmp_path / "candles.db"))] = str(database_path)
    assert main(args) == 1
    assert not database_path.exists() and not private_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "FAILED"
