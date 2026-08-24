"""Tests for bounded single-instrument refresh observability."""

import json
from datetime import datetime, timezone

from investment_terminal.cli import market_data_refresh as cli
from investment_terminal.database.database import Database
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import CandleRepository


CHECKED_AT = datetime(2026, 8, 24, 22, tzinfo=timezone.utc)


def _arguments(tmp_path):
    return [
        "--symbol", "MSFT", "--resolution", "D", "--currency", "USD",
        "--checked-at", CHECKED_AT.isoformat(),
        "--database", str(tmp_path / "market.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--output", str(tmp_path / "report.json"), "--json",
    ]


def _candle(timestamp):
    return Candle(
        symbol="MSFT", resolution="D", timestamp=timestamp,
        open_price=100, high_price=102, low_price=99,
        close_price=101, volume=1000, currency="USD",
    )


def _seed_database(path, candle):
    database = Database(path)
    try:
        database.initialize()
        CandleRepository(database).save(candle)
    finally:
        database.close()


def test_stale_series_is_refreshed_and_reported(monkeypatch, tmp_path, capsys):
    _seed_database(
        tmp_path / "market.db",
        _candle(datetime(2026, 8, 18, 4, tzinfo=timezone.utc)),
    )
    fresh_candle = _candle(datetime(2026, 8, 24, 4, tzinfo=timezone.utc))

    class Client:
        def __init__(self, *, cache_directory):
            assert cache_directory == tmp_path / "cache"

        def get_candles(self, **kwargs):
            assert kwargs["symbol"] == "MSFT"
            return [fresh_candle]

    monkeypatch.setattr(cli, "YahooFinanceClient", Client)

    assert cli.main(_arguments(tmp_path)) == 0
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["status"] == "SUCCESS"
    assert payload["failure"] is None
    assert payload["result"]["refresh_attempted"] is True
    assert payload["result"]["is_ready"] is True
    assert payload["result"]["freshness_before"]["status"] == "STALE"
    assert payload["result"]["freshness_after"]["status"] == "FRESH"
    assert payload["result"]["inserted"] == 1
    assert '"status": "SUCCESS"' in capsys.readouterr().out


def test_already_fresh_series_skips_provider(monkeypatch, tmp_path):
    _seed_database(
        tmp_path / "market.db",
        _candle(datetime(2026, 8, 24, 4, tzinfo=timezone.utc)),
    )

    class Client:
        def __init__(self, *, cache_directory):
            pass

        def get_candles(self, **kwargs):
            raise AssertionError("provider must not be called")

    monkeypatch.setattr(cli, "YahooFinanceClient", Client)

    assert cli.main(_arguments(tmp_path)) == 0
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "SUCCESS"
    assert payload["result"]["refresh_attempted"] is False
    assert payload["result"]["freshness_before"]["status"] == "FRESH"
    assert payload["result"]["freshness_after"]["status"] == "FRESH"
    assert payload["result"]["import"] is None


def test_provider_failure_is_reported_before_nonzero_exit(monkeypatch, tmp_path):
    class Client:
        def __init__(self, *, cache_directory):
            pass

        def get_candles(self, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(cli, "YahooFinanceClient", Client)

    assert cli.main(_arguments(tmp_path)) == 1
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["result"] is None
    assert payload["failure"] == {
        "type": "RuntimeError",
        "reason": "provider unavailable",
    }


def test_database_failure_is_reported_before_nonzero_exit(monkeypatch, tmp_path):
    class FailingDatabase:
        def __init__(self, path):
            raise OSError("database unavailable")

    monkeypatch.setattr(cli, "Database", FailingDatabase)

    assert cli.main(_arguments(tmp_path)) == 1
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["result"] is None
    assert payload["failure"] == {
        "type": "OSError",
        "reason": "database unavailable",
    }


def test_refresh_that_remains_stale_fails_closed(monkeypatch, tmp_path):
    stale_candle = _candle(datetime(2026, 8, 18, 4, tzinfo=timezone.utc))
    _seed_database(tmp_path / "market.db", stale_candle)

    class Client:
        def __init__(self, *, cache_directory):
            pass

        def get_candles(self, **kwargs):
            return [stale_candle]

    monkeypatch.setattr(cli, "YahooFinanceClient", Client)

    assert cli.main(_arguments(tmp_path)) == 1
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "NOT_READY"
    assert payload["failure"] is None
    assert payload["result"]["refresh_attempted"] is True
    assert payload["result"]["is_ready"] is False
    assert payload["result"]["freshness_after"]["status"] == "STALE"
    assert payload["result"]["inserted"] == 0
    assert payload["result"]["duplicates"] == 1
