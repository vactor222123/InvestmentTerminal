from datetime import datetime, timezone

from investment_terminal.operations.yahoo_ticker_match_qualification import (
    YahooTickerMatchQualificationService,
    YahooTickerMatchStatus,
)

NOW = datetime(2026, 8, 27, tzinfo=timezone.utc)


def service():
    return YahooTickerMatchQualificationService(clock=lambda: NOW)


def test_exact_existing_ticker_is_matched_once():
    result = service().qualify(
        instrument_key="de0000000001", exchange_ticker=" abc.de ",
        candidates=[{"symbol": "ABC"}, {"symbol": "abc.de", "exchange": "GER"}],
    )
    assert result.status is YahooTickerMatchStatus.MATCHED
    assert (result.candidate_count, result.exact_match_count) == (2, 1)
    assert result.private_match["exchange_ticker"] == "ABC.DE"
    assert "ABC.DE" not in str(result.report_dict())


def test_no_match_and_duplicate_match_fail_closed():
    no_match = service().qualify(
        instrument_key="DE0000000001", exchange_ticker="ABC.DE",
        candidates=[{"symbol": "ABC"}],
    )
    ambiguous = service().qualify(
        instrument_key="DE0000000001", exchange_ticker="ABC.DE",
        candidates=[{"symbol": "ABC.DE", "exchange": "A"}, {"symbol": "ABC.DE", "exchange": "B"}],
    )
    assert no_match.status is YahooTickerMatchStatus.NO_MATCH
    assert ambiguous.status is YahooTickerMatchStatus.AMBIGUOUS
    assert no_match.private_match is ambiguous.private_match is None


def test_malformed_candidates_return_redacted_failure():
    result = service().qualify(
        instrument_key="DE0000000001", exchange_ticker="PRIVATE", candidates=[{}]
    )
    assert result.status is YahooTickerMatchStatus.FAILED
    assert result.report_dict()["failure"]["type"] == "ValueError"
    assert "PRIVATE" not in str(result.report_dict())
