from datetime import datetime, timezone

import pytest

from investment_terminal.operations.symbol_currency_diagnostic import SymbolCurrencyDiagnosticService
from investment_terminal.operations.symbol_currency_qualification import _checksum
from tests.test_symbol_currency_qualification import checksum, projection


NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)


def checkpoint(value):
    projection_checksum = checksum(value)
    request_checksum = _checksum({"schema_version": 1,
        "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
        "projection_checksum": projection_checksum})
    return {"schema_version": 1, "request_checksum": request_checksum,
            "projection_checksum": projection_checksum, "outcomes": {
                "AAA": {"status": "FINAL_FAILED", "attempt_count": 1,
                        "currency": None, "failure_category": "INVALID_CURRENCY"}}}


class Client:
    def __init__(self): self.calls = []
    def search_symbol(self, symbol):
        self.calls.append(symbol)
        return [{"symbol": symbol}, {"symbol": symbol, "currency": None},
                {"symbol": symbol, "currency": ""},
                {"symbol": symbol, "currency": 1},
                {"symbol": symbol, "currency": "US"},
                {"symbol": symbol, "currency": "usd"},
                {"symbol": "OTHER", "currency": "EUR"}]


def test_reports_only_field_shapes_for_first_invalid_currency():
    value = projection(); client = Client()
    report = SymbolCurrencyDiagnosticService(client=client, clock=lambda: NOW).run(
        value, checksum(value), checkpoint(value))
    assert client.calls == ["AAA"]
    assert report["coverage"] == {"result_count": 7, "exact_match_count": 6,
        "currency_field_shapes": {"missing": 1, "null": 1, "empty": 1,
            "non_string": 1, "invalid_format": 1, "valid_format": 1},
        "distinct_valid_currency_count": 1}
    assert "AAA" not in str(report) and "USD" not in str(report)


def test_fails_closed_without_matching_outcome_or_checksum():
    value = projection(); service = SymbolCurrencyDiagnosticService(
        client=Client(), clock=lambda: NOW)
    with pytest.raises(ValueError, match="Projection checksum"):
        service.run(value, "0" * 64, checkpoint(value))
    evidence = checkpoint(value); evidence["outcomes"] = {}
    with pytest.raises(ValueError, match="No terminal"):
        service.run(value, checksum(value), evidence)
