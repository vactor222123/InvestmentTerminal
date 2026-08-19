"""Tests for bounded Yahoo historical-candle qualification."""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.models.candle import Candle
from investment_terminal.operations.yahoo_candle_qualification import (
    YahooCandleQualificationRequest,
    YahooCandleQualificationService,
    YahooCandleQualificationStatus,
)
from investment_terminal.utils.exceptions import APIError


START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 10, tzinfo=timezone.utc)
RUN_START = datetime(2026, 8, 19, 10, 0, tzinfo=timezone.utc)
RUN_END = RUN_START + timedelta(seconds=2)


class StaticClient:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def get_candles(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def request() -> YahooCandleQualificationRequest:
    return YahooCandleQualificationRequest(
        symbol=" msft ",
        resolution="d",
        currency="usd",
        requested_start=START,
        requested_end=END,
    )


def candle(day: int, *, symbol: str = "MSFT") -> Candle:
    return Candle(
        symbol=symbol,
        resolution="D",
        timestamp=START + timedelta(days=day),
        open_price=100,
        high_price=102,
        low_price=99,
        close_price=101,
        volume=1000,
        currency="USD",
    )


def clock():
    values = iter((RUN_START, RUN_END))
    return lambda: next(values)


def qualify(result):
    client = StaticClient(result)
    report = YahooCandleQualificationService(
        client=client,
        clock=clock(),
    ).qualify(request())
    return report, client


def test_success_preserves_bounded_coverage_and_duration() -> None:
    report, client = qualify([candle(1), candle(2)])

    assert report.status is YahooCandleQualificationStatus.SUCCESS
    assert report.candle_count == 2
    assert report.earliest_candle_at == START + timedelta(days=1)
    assert report.latest_candle_at == START + timedelta(days=2)
    assert report.duration_seconds == 2
    assert client.calls == [
        {
            "symbol": "MSFT",
            "resolution": "D",
            "start": START,
            "end": END,
            "currency": "USD",
        }
    ]


def test_empty_provider_result_is_not_reported_as_success() -> None:
    report, _ = qualify([])

    assert report.status is YahooCandleQualificationStatus.EMPTY
    assert report.candle_count == 0
    assert report.failure_type is None


def test_provider_failure_becomes_visible_failed_report() -> None:
    report, _ = qualify(APIError("provider unavailable"))

    assert report.status is YahooCandleQualificationStatus.FAILED
    assert report.candle_count is None
    assert report.failure_type == "APIError"
    assert report.failure_reason == "provider unavailable"


@pytest.mark.parametrize(
    "provider_result",
    [
        (candle(2), candle(1)),
        [candle(1), candle(1)],
        [candle(1, symbol="AAPL")],
        [candle(10)],
        "not-a-list",
        [object()],
    ],
)
def test_malformed_provider_output_fails_closed(provider_result) -> None:
    report, _ = qualify(provider_result)

    assert report.status is YahooCandleQualificationStatus.FAILED
    assert report.failure_type in {"TypeError", "ValueError"}


def test_request_rejects_naive_or_invalid_window() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        YahooCandleQualificationRequest(
            symbol="MSFT",
            resolution="D",
            currency="USD",
            requested_start=datetime(2026, 8, 1),
            requested_end=END,
        )
    with pytest.raises(ValueError, match="earlier"):
        YahooCandleQualificationRequest(
            symbol="MSFT",
            resolution="D",
            currency="USD",
            requested_start=END,
            requested_end=START,
        )


def test_clock_moving_backwards_fails_closed() -> None:
    service = YahooCandleQualificationService(
        client=StaticClient([]),
        clock=iter((RUN_END, RUN_START)).__next__,
    )

    with pytest.raises(ValueError, match="moved backwards"):
        service.qualify(request())


def test_serialized_report_denies_broad_claims_and_authority() -> None:
    report, _ = qualify([candle(1)])
    payload = report.to_dict()

    assert payload["schema_version"] == 1
    assert payload["provider_identity"] == "YAHOO_FINANCE"
    assert payload["failure"] is None
    assert any("20-year" in item for item in payload["limitations"])
    assert any("trading" in item for item in payload["limitations"])
