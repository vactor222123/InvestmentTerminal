from datetime import datetime, timezone
import json

import pytest

from investment_terminal.cli.universe_eligibility_scan import main
from investment_terminal.models.candle import Candle
from investment_terminal.utils.atomic_write import write_json_atomic


NOW = datetime(2026, 8, 29, tzinfo=timezone.utc)


def _universe():
    return {
        "schema_version": 1,
        "universe_identity": "BROAD_US_LISTED_SECURITIES",
        "source_identity": "NASDAQ_TRADER_SYMBOL_DIRECTORY",
        "archive_sha256": {
            "NASDAQ_LISTED": "a" * 64,
            "OTHER_LISTED": "b" * 64,
        },
        "members": [
            {
                "source": "NASDAQ_LISTED",
                "source_symbol": "AAA",
                "yahoo_symbol": "AAA",
                "security_name": "Alpha",
                "listing_code": "Q",
                "is_etf": False,
            }
        ],
    }


class Client:
    def __init__(self):
        self.calls = 0

    def get_candles(self, *, symbol, resolution, start, end, currency):
        self.calls += 1
        return [
            Candle(
                symbol=symbol,
                resolution=resolution,
                timestamp=NOW,
                open_price=1,
                high_price=1,
                low_price=1,
                close_price=1,
                volume=1,
                currency=currency,
            )
        ]


def _arguments(tmp_path):
    universe = tmp_path / "universe.json"
    checkpoint = tmp_path / "checkpoint.json"
    report = tmp_path / "report.json"
    universe.write_text(json.dumps(_universe()), encoding="utf-8")
    return [
        "--universe",
        str(universe),
        "--checkpoint",
        str(checkpoint),
        "--cache-directory",
        str(tmp_path / "cache"),
        "--report-output",
        str(report),
        "--window-end",
        "2026-08-30T00:00:00+00:00",
    ], checkpoint, report


def test_cli_writes_private_checkpoint_and_redacted_complete_report(tmp_path):
    arguments, checkpoint, report = _arguments(tmp_path)
    client = Client()
    assert main(arguments, client=client, clock=lambda: NOW) == 0
    private = json.loads(checkpoint.read_text(encoding="utf-8"))
    public = json.loads(report.read_text(encoding="utf-8"))
    assert private["schema_version"] == 2
    assert public["schema_version"] == 2
    assert private["outcomes"]["NASDAQ_LISTED:AAA"]["yahoo_symbol"] == "AAA"
    assert public["status"] == "COMPLETE"
    assert "AAA" not in report.read_text(encoding="utf-8")


def test_cli_failure_report_is_redacted_and_nonzero(tmp_path):
    arguments, _, report = _arguments(tmp_path)
    arguments[-1] = "not-a-date"
    assert main(arguments, client=Client(), clock=lambda: NOW) == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["status"] == "FAILED"
    assert payload["failure"] == {
        "type": "ValueError",
        "reason": "Universe eligibility scan failed",
    }
    assert "not-a-date" not in report.read_text(encoding="utf-8")


def test_report_write_failure_does_not_erase_completed_checkpoint(tmp_path):
    arguments, checkpoint, report = _arguments(tmp_path)

    def writer(path, payload):
        if path == report:
            raise OSError("report destination unavailable")
        return write_json_atomic(path, payload)

    with pytest.raises(OSError, match="report destination"):
        main(arguments, client=Client(), clock=lambda: NOW, writer=writer)
    assert checkpoint.exists()
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["outcomes"]


def test_cli_exact_resume_performs_zero_provider_calls(tmp_path):
    arguments, _, report = _arguments(tmp_path)
    first = Client()
    assert main(arguments, client=first, clock=lambda: NOW) == 0
    second = Client()
    assert main(arguments, client=second, clock=lambda: NOW) == 0
    assert second.calls == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["coverage"]["current_run"]["attempted_count"] == 0
