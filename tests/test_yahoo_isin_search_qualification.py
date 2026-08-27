"""Tests for privacy-safe Yahoo ISIN-search qualification."""

from datetime import datetime, timezone

from investment_terminal.operations.yahoo_isin_search_qualification import (
    YahooIsinSearchQualificationService,
    YahooIsinSearchStatus,
)

NOW = datetime(2026, 8, 27, 18, tzinfo=timezone.utc)


class Client:
    def __init__(self, value): self.value = value; self.calls = []
    def search_isin(self, isin):
        self.calls.append(isin)
        if isinstance(self.value, Exception): raise self.value
        return self.value


def test_qualification_normalizes_sorts_and_deduplicates_candidates():
    client = Client([
        {"symbol": " zzz.de ", "exchange": "ger", "exchDisp": "Xetra",
         "quoteType": "equity", "currency": "eur", "longname": "PRIVATE"},
        {"symbol": "AAA", "exchange": "nyq", "quoteType": "equity", "currency": "usd"},
        {"symbol": "ZZZ.DE", "exchange": "GER", "exchDisp": "Xetra",
         "quoteType": "EQUITY", "currency": "EUR"},
    ])
    result = YahooIsinSearchQualificationService(client=client, clock=lambda: NOW).qualify(
        " de0000000001 "
    )
    assert client.calls == ["DE0000000001"]
    assert result.status is YahooIsinSearchStatus.SUCCESS
    assert [item.symbol for item in result.candidates] == ["AAA", "ZZZ.DE"]
    assert result.report_dict()["coverage"] == {
        "candidate_count": 2, "unique_symbol_count": 2, "unique_exchange_count": 2,
    }
    assert "PRIVATE" not in str(result.private_dict())


def test_empty_search_is_visible():
    result = YahooIsinSearchQualificationService(
        client=Client([]), clock=lambda: NOW
    ).qualify("DE0000000001")
    assert result.status is YahooIsinSearchStatus.EMPTY
    assert result.report_dict()["coverage"]["candidate_count"] == 0


def test_provider_failure_is_redacted_with_unknown_coverage():
    result = YahooIsinSearchQualificationService(
        client=Client(OSError("SECRET_PROVIDER_DETAIL")), clock=lambda: NOW
    ).qualify("DE0000000001")
    report = result.report_dict()
    assert result.status is YahooIsinSearchStatus.FAILED
    assert report["coverage"]["candidate_count"] is None
    assert report["failure"]["type"] == "OSError"
    assert "SECRET_PROVIDER_DETAIL" not in str(report)


def test_malformed_candidate_fails_closed():
    result = YahooIsinSearchQualificationService(
        client=Client([{"exchange": "GER"}]), clock=lambda: NOW
    ).qualify("DE0000000001")
    assert result.status is YahooIsinSearchStatus.FAILED
    assert result.failure_type == "ValueError"
