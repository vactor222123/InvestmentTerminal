from datetime import datetime, timezone
import json

import pandas as pd

from investment_terminal.cli.single_series_candle_diagnostic import main
from investment_terminal.operations.universe_eligibility_scan import EligibilityScanRequest


NOW = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _files(tmp_path):
    universe = {
        "schema_version": 1, "universe_identity": "BROAD_US_LISTED_SECURITIES",
        "source_identity": "NASDAQ_TRADER_SYMBOL_DIRECTORY",
        "archive_sha256": {"NASDAQ_LISTED": "a" * 64, "OTHER_LISTED": "b" * 64},
        "members": [{"source": "NASDAQ_LISTED", "source_symbol": "PRIVATE",
                     "yahoo_symbol": "PRIVATE", "security_name": "Private Name",
                     "listing_code": "Q", "is_etf": False}],
    }
    request = EligibilityScanRequest.from_universe(universe, requested_end=NOW)
    outcome = {"source": "NASDAQ_LISTED", "source_symbol": "PRIVATE",
               "yahoo_symbol": "PRIVATE", "status": "FINAL_FAILED", "attempt_count": 3,
               "provider_instrument_type": None, "observed_start": None,
               "observed_end": None, "candle_count": None,
               "positive_volume_day_count": None, "median_daily_traded_value": None,
               "measured_at": NOW.isoformat(), "failure_category": "RESPONSE_NUMERIC"}
    checkpoint = {"schema_version": 3, "request_checksum": request.checksum,
                  "universe_checksum": request.universe_checksum,
                  "requested_start": request.requested_start.isoformat(),
                  "requested_end": request.requested_end.isoformat(),
                  "outcomes": {"NASDAQ_LISTED:PRIVATE": outcome}}
    universe_path = tmp_path / "universe.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    report_path = tmp_path / "report.json"
    universe_path.write_text(json.dumps(universe), encoding="utf-8")
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    arguments = ["--universe", str(universe_path), "--checkpoint", str(checkpoint_path),
                 "--cache-directory", str(tmp_path / "cache"),
                 "--report-output", str(report_path), "--window-end", NOW.isoformat()]
    return arguments, checkpoint_path, report_path


class Client:
    def get_daily_frame(self, **kwargs):
        return pd.DataFrame(
            {"Open": [float("nan")], "High": [2.0], "Low": [1.0],
             "Close": [1.5], "Volume": [1.0]},
            index=[pd.Timestamp("2026-08-29", tz="UTC")],
        )


def test_cli_writes_redacted_report_and_never_changes_checkpoint(tmp_path):
    arguments, checkpoint, report = _files(tmp_path)
    original = checkpoint.read_bytes()
    assert main(arguments, client=Client(), clock=lambda: NOW) == 0
    assert checkpoint.read_bytes() == original
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "SUCCESS"
    assert payload["coverage"]["invalid_reason_counts"] == {"OPEN_NON_FINITE": 1}
    assert "PRIVATE" not in report.read_text(encoding="utf-8")


def test_cli_failure_is_redacted_nonzero_and_preserves_checkpoint(tmp_path):
    arguments, checkpoint, report = _files(tmp_path)
    original = checkpoint.read_bytes()
    arguments[-1] = "not-a-date"
    assert main(arguments, client=Client(), clock=lambda: NOW) == 1
    assert checkpoint.read_bytes() == original
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["failure"] == {
        "type": "ValueError",
        "reason": "Single-series raw candle diagnostic failed",
    }
    assert "not-a-date" not in report.read_text(encoding="utf-8")
