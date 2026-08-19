"""Tests for bounded Yahoo candle ingestion CLI."""

import json
from datetime import datetime, timezone

from investment_terminal.cli import yahoo_candle_ingestion as cli
from investment_terminal.models.candle import Candle


def _arguments(tmp_path):
    return [
        "--symbol", "MSFT", "--resolution", "D",
        "--start", "2026-08-01T00:00:00+00:00",
        "--end", "2026-08-10T00:00:00+00:00",
        "--database", str(tmp_path / "market.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--output", str(tmp_path / "report.json"), "--json",
    ]


def test_ingestion_persists_and_reports_duplicates(monkeypatch, tmp_path, capsys):
    candle = Candle(
        symbol="MSFT", resolution="D",
        timestamp=datetime(2026, 8, 3, tzinfo=timezone.utc),
        open_price=100, high_price=102, low_price=99,
        close_price=101, volume=1000, currency="USD",
    )

    class Client:
        def __init__(self, *, cache_directory):
            assert cache_directory == tmp_path / "cache"

        def get_candles(self, **kwargs):
            return [candle]

    monkeypatch.setattr(cli, "YahooFinanceClient", Client)

    assert cli.main(_arguments(tmp_path)) == 0
    assert cli.main(_arguments(tmp_path)) == 0

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "SUCCESS"
    assert payload["downloaded"] == 1
    assert payload["inserted"] == 0
    assert payload["duplicates"] == 1
    assert payload["stored_total"] == 1
    assert payload["schema_version"] == 2
    assert payload["coverage"] == {
        "candle_count": 1,
        "earliest_candle_at": "2026-08-03T00:00:00+00:00",
        "latest_candle_at": "2026-08-03T00:00:00+00:00",
        "observed_span_days": 0.0,
    }
    assert '"status": "SUCCESS"' in capsys.readouterr().out


def test_failure_is_reported_before_nonzero_exit(monkeypatch, tmp_path):
    class Client:
        def __init__(self, *, cache_directory):
            pass

        def get_candles(self, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(cli, "YahooFinanceClient", Client)

    assert cli.main(_arguments(tmp_path)) == 1
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["coverage"] is None
    assert payload["failure"] == {
        "type": "RuntimeError",
        "reason": "provider unavailable",
    }
