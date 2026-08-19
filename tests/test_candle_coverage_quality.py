"""Tests for explicit-session daily candle coverage quality."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from investment_terminal.history.historical_local_session_calendar import (
    HistoricalLocalSessionCalendar,
)
from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
    HistoricalSessionCalendarIdentity,
)
from investment_terminal.models.candle import Candle
from investment_terminal.history.candle_coverage_quality import (
    CandleCoverageQualityService,
)


NEW_YORK = ZoneInfo("America/New_York")
START = datetime(2026, 8, 3, tzinfo=timezone.utc)
END = datetime(2026, 8, 6, 23, 59, tzinfo=timezone.utc)


def calendar() -> HistoricalLocalSessionCalendar:
    identity = HistoricalSessionCalendarIdentity(
        calendar_id="XNYS",
        version=1,
        timezone="America/New_York",
        source="TEST_FIXTURE",
    )
    sessions = tuple(
        HistoricalMarketSession(
            session_key=f"XNYS:2026-08-0{day}",
            session_date=date(2026, 8, day),
            opens_at=datetime(2026, 8, day, 9, 30, tzinfo=NEW_YORK),
            closes_at=datetime(2026, 8, day, 16, 0, tzinfo=NEW_YORK),
            calendar=identity,
        )
        for day in (3, 4, 5)
    )
    return HistoricalLocalSessionCalendar(identity=identity, sessions=sessions)


def candle(day: int) -> Candle:
    return Candle(
        symbol="MSFT",
        resolution="D",
        timestamp=datetime(2026, 8, day, 4, tzinfo=timezone.utc),
        open_price=100,
        high_price=102,
        low_price=99,
        close_price=101,
        volume=1000,
        currency="USD",
    )


def evaluate(candles):
    return CandleCoverageQualityService().evaluate(
        symbol="msft",
        resolution="d",
        start_at=START,
        end_at=END,
        candles=candles,
        calendar=calendar(),
    )


def test_complete_explicit_session_coverage() -> None:
    result = evaluate((candle(3), candle(4), candle(5)))

    assert result.expected_session_count == 3
    assert result.observed_session_count == 3
    assert result.completeness_ratio == 1.0
    assert result.is_complete is True
    assert result.missing_session_keys == ()
    assert result.unexpected_candle_timestamps == ()
    assert result.to_dict()["calendar_identity"] == "XNYS@1"


def test_missing_and_unexpected_dates_remain_visible() -> None:
    result = evaluate((candle(3), candle(5), candle(6)))

    assert result.observed_session_count == 2
    assert result.missing_session_keys == ("XNYS:2026-08-04",)
    assert result.unexpected_candle_timestamps == (candle(6).timestamp,)
    assert result.completeness_ratio == pytest.approx(2 / 3)
    assert result.is_complete is False


def test_empty_calendar_does_not_claim_complete_coverage() -> None:
    identity = calendar().identity
    empty = HistoricalLocalSessionCalendar(identity=identity, sessions=())

    result = CandleCoverageQualityService().evaluate(
        symbol="MSFT",
        resolution="D",
        start_at=START,
        end_at=END,
        candles=(),
        calendar=empty,
    )

    assert result.completeness_ratio is None
    assert result.is_complete is False


def test_rejects_non_daily_or_mismatched_candles() -> None:
    with pytest.raises(ValueError, match="supports D only"):
        CandleCoverageQualityService().evaluate(
            symbol="MSFT",
            resolution="W",
            start_at=START,
            end_at=END,
            candles=(),
            calendar=calendar(),
        )

    with pytest.raises(ValueError, match="match symbol"):
        CandleCoverageQualityService().evaluate(
            symbol="AAPL",
            resolution="D",
            start_at=START,
            end_at=END,
            candles=(candle(3),),
            calendar=calendar(),
        )
