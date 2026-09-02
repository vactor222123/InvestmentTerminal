from datetime import datetime, timezone
from hashlib import sha256
import json

import pytest
from yfinance.exceptions import YFRateLimitError

from investment_terminal.operations.symbol_currency_qualification import SymbolCurrencyQualificationService


NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)


def projection():
    return {"schema_version": 1, "projection_identity": "ELIGIBILITY_SUCCESS_UNIVERSE",
            "request_checksum": "a" * 64, "universe_checksum": "b" * 64,
            "members": [{"source": "TEST", "source_symbol": value,
                         "yahoo_symbol": value} for value in ("CCC", "AAA", "BBB", "DDD")]}


def checksum(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()


class Client:
    def __init__(self):
        self.calls = []

    def search_symbol(self, symbol):
        self.calls.append(symbol)
        if symbol == "CCC":
            raise RuntimeError("private") from YFRateLimitError()
        if symbol == "BBB":
            return [{"symbol": "BBB", "currency": "USD"},
                    {"symbol": "bbb", "currency": "CAD"}]
        return [{"symbol": symbol, "currency": "usd"},
                {"symbol": "FUZZY", "currency": "EUR"}]


def test_qualifies_exact_currency_and_halts_on_rate_limit():
    value = projection(); client = Client(); writes = []
    report = SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW
    ).run(value, checksum(value), max_items=100)

    assert client.calls == ["AAA", "BBB", "CCC"]
    assert report["status"] == "HALTED"
    assert report["halt_category"] == "RATE_LIMITED"
    assert report["coverage"] == {"member_count": 4, "attempted_count": 3,
        "success_count": 1, "final_failure_count": 1,
        "retry_pending_count": 1, "never_attempted_count": 1}
    assert writes[-1]["outcomes"]["AAA"]["currency"] == "USD"
    assert "AAA" not in str(report) and "USD" not in str(report)


def test_resume_skips_terminal_and_completes(monkeypatch):
    value = projection(); writes = []; client = Client()
    service = SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW)
    service.run(value, checksum(value), max_items=100)
    client.search_symbol = lambda symbol: [{"symbol": symbol, "currency": "USD"}]
    report = service.run(value, checksum(value), writes[-1], max_items=100)
    assert report["status"] == "COMPLETE"
    assert report["coverage"]["success_count"] == 3
    assert report["coverage"]["final_failure_count"] == 1


def test_rejects_projection_and_checkpoint_mismatch_before_provider_call():
    value = projection(); client = Client()
    service = SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=lambda value: None, clock=lambda: NOW)
    with pytest.raises(ValueError, match="Projection checksum"):
        service.run(value, "0" * 64, max_items=1)
    with pytest.raises(ValueError, match="Checkpoint does not match"):
        service.run(value, checksum(value), {"schema_version": 1}, max_items=1)
    assert client.calls == []


def test_exact_result_without_valid_currency_is_terminal_and_typed():
    value = projection(); writes = []

    class MissingCurrency:
        def search_symbol(self, symbol):
            return [{"symbol": symbol, "currency": None}]

    report = SymbolCurrencyQualificationService(
        client=MissingCurrency(), checkpoint_writer=writes.append, clock=lambda: NOW
    ).run(value, checksum(value), max_items=1)
    assert writes[-1]["outcomes"]["AAA"]["status"] == "FINAL_FAILED"
    assert writes[-1]["outcomes"]["AAA"]["failure_category"] == "INVALID_CURRENCY"
    assert report["failure_categories"] == ["INVALID_CURRENCY"]


@pytest.mark.parametrize("max_items", [0, 101, True])
def test_rejects_invalid_item_bound(max_items):
    value = projection()
    with pytest.raises((TypeError, ValueError)):
        SymbolCurrencyQualificationService(
            client=Client(), checkpoint_writer=lambda value: None, clock=lambda: NOW
        ).run(value, checksum(value), max_items=max_items)
