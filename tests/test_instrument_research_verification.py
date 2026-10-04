"""Offline private/report parity and privacy-safe CLI failure paths."""

from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json

import pytest

from investment_terminal.cli.instrument_research_export import main as export_main
from investment_terminal.cli.instrument_research_verify import main as verify_main
from investment_terminal.operations.instrument_research_export import (
    build_instrument_research_export,
)
from investment_terminal.operations.instrument_research_verification import (
    verify_instrument_research_export,
)
from tests.test_instrument_research_export import _cli_args
from tests.test_instrument_research_export import _fixture
from tests.test_weekly_candle_refresh import END


def _evidence(tmp_path):
    export_args, private_path, report_path, _ = _cli_args(tmp_path)
    assert export_main(export_args) == 0
    report_directory = tmp_path / "reports"
    report_directory.mkdir()
    relocated_report = report_directory / report_path.name
    report_path.replace(relocated_report)
    symbol = export_args[export_args.index("--symbol") + 1]
    report_sha256 = sha256(relocated_report.read_bytes()).hexdigest()
    verify_args = [
        "--private-export", str(private_path),
        "--report", str(relocated_report),
        "--report-sha256", report_sha256,
        "--symbol", symbol,
    ]
    return private_path, relocated_report, verify_args


def _option(args, flag, value):
    updated = args.copy()
    updated[updated.index(flag) + 1] = str(value)
    return updated


def test_local_verifier_accepts_bound_pair_without_writes(tmp_path, capsys):
    private_path, report_path, args = _evidence(tmp_path)
    before_private = private_path.read_bytes()
    before_report = report_path.read_bytes()
    assert verify_main(args) == 0
    output = capsys.readouterr().out
    assert "VERIFIED:" in output
    assert sha256(before_private).hexdigest() in output
    assert str(private_path) not in output
    assert private_path.read_bytes() == before_private
    assert report_path.read_bytes() == before_report


def test_verifier_recomputes_full_200_close_indicator_sample(tmp_path):
    fixture = _fixture(tmp_path, count=200)
    _, _, _, plan, database, checkpoint, projection, _, projection_digest = fixture
    private, report = build_instrument_research_export(
        plan, checkpoint, projection, projection_digest, database.connection,
        symbol=plan.items[0][0], history_start=END - timedelta(days=200),
    )
    verify_instrument_research_export(
        private, report, expected_symbol=plan.items[0][0],
    )
    private["indicator"]["sma200_raw_close"] += 1
    with pytest.raises(ValueError, match="indicator values"):
        verify_instrument_research_export(
            private, report, expected_symbol=plan.items[0][0],
        )
    database.close()


@pytest.mark.parametrize("change", [
    "wrong_symbol", "missing_private", "missing_report", "wrong_report_hash",
    "private_under_reports", "changed_candle", "changed_binding",
    "malformed_private", "nonfinite_private", "duplicate_key",
])
def test_local_verifier_fails_closed_without_private_details(
        tmp_path, capsys, change):
    private_path, report_path, args = _evidence(tmp_path)
    if change == "wrong_symbol":
        args = _option(args, "--symbol", "WRONG")
    elif change == "missing_private":
        args = _option(args, "--private-export", tmp_path / "missing.json")
    elif change == "missing_report":
        args = _option(args, "--report", tmp_path / "missing.json")
    elif change == "wrong_report_hash":
        args = _option(args, "--report-sha256", "0" * 64)
    elif change == "private_under_reports":
        relocated = report_path.parent / "private.json"
        private_path.replace(relocated)
        args = _option(args, "--private-export", relocated)
    elif change in ("changed_candle", "changed_binding"):
        private = json.loads(private_path.read_text(encoding="utf-8"))
        if change == "changed_candle":
            private["candles"][0]["close_price"] += 1
        else:
            private["source_projection_sha256"] = "0" * 64
        private_path.write_text(json.dumps(private), encoding="utf-8")
    elif change == "malformed_private":
        private_path.write_text("{", encoding="utf-8")
    elif change == "nonfinite_private":
        private_path.write_text('{"value": NaN}', encoding="utf-8")
    else:
        private_path.write_text('{"value": 1, "value": 2}', encoding="utf-8")
    assert verify_main(args) == 1
    result = capsys.readouterr()
    assert result.out == ""
    assert "verification failed" in result.err
    assert str(private_path) not in result.err
    assert "WRONG" not in result.err


@pytest.mark.parametrize("change", [
    "report_count", "indicator_symbol", "indicator_sample", "report_limitations",
    "indicator_latest", "indicator_sma", "candle_order", "candle_ohlc",
    "report_sample_bool", "report_recent_int", "short_window", "window",
    "bad_schema",
])
def test_parity_rejects_changed_contract_fields(tmp_path, change):
    private_path, report_path, args = _evidence(tmp_path)
    private = json.loads(private_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if change == "report_count":
        report["candle_count"] += 1
    elif change == "indicator_symbol":
        private["indicator"]["symbol"] = "OTHER"
    elif change == "indicator_sample":
        private["indicator"]["sample_count_capped_at_200"] += 1
    elif change == "report_limitations":
        report["limitations"].append("private value")
    elif change == "indicator_latest":
        private["indicator"]["latest_raw_close"] += 1
    elif change == "indicator_sma":
        private["indicator"]["sma50_raw_close"] = 1.0
    elif change == "report_sample_bool":
        report["sample_count_capped_at_200"] = True
    elif change == "report_recent_int":
        report["recent_7_calendar_day_proxy"] = 1
    elif change == "candle_order":
        private["candles"] = list(reversed(private["candles"]))
    elif change == "candle_ohlc":
        private["candles"][0]["high_price"] = 1
    elif change == "short_window":
        private["candles"] = private["candles"][-1:]
        private["candle_count"] = 1
        report["candle_count"] = 1
        digest = sha256(json.dumps(
            private["candles"], sort_keys=True, separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")).hexdigest()
        private["history_candles_sha256"] = digest
        report["history_candles_sha256"] = digest
    elif change == "window":
        private["history_start"] = "2010-01-01T00:00:00+00:00"
        report["history_start"] = private["history_start"]
    else:
        private["schema_version"] = True
        report["schema_version"] = True
    with pytest.raises(ValueError):
        verify_instrument_research_export(
            private, report, expected_symbol=args[-1],
        )


def test_verifier_rejects_report_with_matching_new_hash_but_changed_binding(tmp_path):
    private_path, report_path, args = _evidence(tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    changed = deepcopy(report)
    changed["selection_checksum"] = "0" * 64
    report_path.write_text(json.dumps(changed), encoding="utf-8")
    args = _option(args, "--report-sha256", sha256(report_path.read_bytes()).hexdigest())
    assert verify_main(args) == 1
