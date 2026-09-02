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

    def get_currency(self, symbol):
        self.calls.append(symbol)
        if symbol == "CCC":
            raise RuntimeError("private") from YFRateLimitError()
        if symbol == "BBB":
            raise ValueError("private")
        return "USD"


def test_qualifies_exact_currency_and_halts_on_rate_limit():
    value = projection(); client = Client(); writes = []
    report = SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW
    ).run(value, checksum(value), max_items=100)

    assert client.calls == ["AAA", "BBB", "CCC"]
    assert report["status"] == "HALTED"
    assert report["halt_category"] == "RATE_LIMITED"
    assert report["coverage"] == {"member_count": 4, "attempted_count": 3,
        "success_count": 1, "final_failure_count": 0,
        "retry_pending_count": 2, "never_attempted_count": 1}
    assert writes[-1]["schema_version"] == 2
    assert writes[-1]["outcomes"]["AAA"]["currency"] == "USD"
    assert "AAA" not in str(report) and "USD" not in str(report)


def test_resume_skips_terminal_and_completes(monkeypatch):
    value = projection(); writes = []; client = Client()
    service = SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW)
    service.run(value, checksum(value), max_items=100)
    client.get_currency = lambda symbol: "USD"
    report = service.run(value, checksum(value), writes[-1], max_items=100)
    assert report["status"] == "COMPLETE"
    assert report["coverage"]["success_count"] == 4
    assert report["coverage"]["final_failure_count"] == 0


def test_rejects_projection_and_checkpoint_mismatch_before_provider_call():
    value = projection(); client = Client()
    service = SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=lambda value: None, clock=lambda: NOW)
    with pytest.raises(ValueError, match="Projection checksum"):
        service.run(value, "0" * 64, max_items=1)
    with pytest.raises(ValueError, match="Checkpoint does not match"):
        service.run(value, checksum(value), {"schema_version": 1}, max_items=1)
    assert client.calls == []


def test_migrates_before_provider_and_reopens_only_invalid_currency():
    value = projection(); writes = []; client = Client()
    legacy_request = checksum({"schema_version": 1,
        "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
        "projection_checksum": checksum(value)})
    legacy = {"schema_version": 1, "request_checksum": legacy_request,
        "projection_checksum": checksum(value), "outcomes": {
            "AAA": {"status": "FINAL_FAILED", "attempt_count": 1,
                    "currency": None, "failure_category": "INVALID_CURRENCY"},
            "BBB": {"status": "FINAL_FAILED", "attempt_count": 1,
                    "currency": None, "failure_category": "NO_EXACT_MATCH"}}}

    SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW
    ).run(value, checksum(value), legacy, max_items=1)

    assert writes[0]["schema_version"] == 2
    assert writes[0]["outcomes"]["AAA"]["status"] == "RETRY_PENDING"
    assert writes[0]["outcomes"]["BBB"]["status"] == "FINAL_FAILED"
    assert client.calls == ["AAA"]


def test_new_checkpoint_uses_chart_metadata_directly():
    value = projection(); writes = []; client = Client()
    report = SymbolCurrencyQualificationService(
        client=client, checkpoint_writer=writes.append, clock=lambda: NOW
    ).run(value, checksum(value), max_items=1)
    assert client.calls == ["AAA"]
    assert report["schema_version"] == 2
    assert report["provider_identity"] == "YAHOO_FINANCE_CHART_METADATA"


def test_migration_write_failure_prevents_provider_call():
    value = projection(); client = Client()
    legacy_request = checksum({"schema_version": 1,
        "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
        "projection_checksum": checksum(value)})
    legacy = {"schema_version": 1, "request_checksum": legacy_request,
        "projection_checksum": checksum(value), "outcomes": {
            "AAA": {"status": "FINAL_FAILED", "attempt_count": 1,
                    "currency": None, "failure_category": "INVALID_CURRENCY"}}}

    def fail_write(value):
        raise OSError("private")

    with pytest.raises(OSError, match="private"):
        SymbolCurrencyQualificationService(
            client=client, checkpoint_writer=fail_write, clock=lambda: NOW
        ).run(value, checksum(value), legacy, max_items=1)
    assert client.calls == []


@pytest.mark.parametrize("max_items", [0, 101, True])
def test_rejects_invalid_item_bound(max_items):
    value = projection()
    with pytest.raises((TypeError, ValueError)):
        SymbolCurrencyQualificationService(
            client=Client(), checkpoint_writer=lambda value: None, clock=lambda: NOW
        ).run(value, checksum(value), max_items=max_items)
