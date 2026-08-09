"""
Tests for deterministic trading-session observation windows.
"""

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
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
)
from investment_terminal.history.historical_trading_session_window import (
    HistoricalTradingSessionWindowPolicy,
)


BERLIN = ZoneInfo("Europe/Berlin")


def identity() -> HistoricalSessionCalendarIdentity:
    return HistoricalSessionCalendarIdentity(
        calendar_id="XETRA",
        version=1,
        timezone="Europe/Berlin",
        source="LOCAL_SESSION_FIXTURE",
    )


def make_session(
    year: int,
    month: int,
    day: int,
    *,
    calendar: HistoricalSessionCalendarIdentity,
) -> HistoricalMarketSession:
    return HistoricalMarketSession(
        session_key=f"XETRA:{year:04d}-{month:02d}-{day:02d}",
        session_date=date(year, month, day),
        opens_at=datetime(
            year,
            month,
            day,
            9,
            0,
            tzinfo=BERLIN,
        ),
        closes_at=datetime(
            year,
            month,
            day,
            17,
            30,
            tzinfo=BERLIN,
        ),
        calendar=calendar,
    )


def policy_with_sessions(
    *days: int,
) -> HistoricalTradingSessionWindowPolicy:
    cal = identity()
    return HistoricalTradingSessionWindowPolicy(
        HistoricalLocalSessionCalendar(
            identity=cal,
            sessions=tuple(
                make_session(
                    2026,
                    8,
                    day,
                    calendar=cal,
                )
                for day in days
            ),
        )
    )


def test_one_trading_session_after_friday_skips_weekend_explicitly() -> None:
    policy = policy_with_sessions(7, 10, 11)
    origin = datetime(
        2026,
        8,
        7,
        18,
        0,
        tzinfo=BERLIN,
    )
    monday_close = datetime(
        2026,
        8,
        10,
        17,
        30,
        tzinfo=BERLIN,
    )

    result = policy.resolve(
        origin_at=origin,
        window=HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=1,
        ),
        as_of=monday_close,
    )

    assert result.endpoint_session.session_date == date(
        2026,
        8,
        10,
    )
    assert result.endpoint_at == monday_close.astimezone(
        timezone.utc
    )
    assert result.counted_session_keys == (
        "XETRA:2026-08-10",
    )
    assert result.is_mature is True


def test_session_open_equal_to_origin_is_excluded() -> None:
    policy = policy_with_sessions(10, 11)
    origin = datetime(
        2026,
        8,
        10,
        9,
        0,
        tzinfo=BERLIN,
    )

    result = policy.resolve(
        origin_at=origin,
        window=HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=1,
        ),
        as_of=datetime(
            2026,
            8,
            11,
            17,
            30,
            tzinfo=BERLIN,
        ),
    )

    assert result.endpoint_session.session_date == date(
        2026,
        8,
        11,
    )


def test_window_value_selects_nth_explicit_future_session() -> None:
    policy = policy_with_sessions(10, 11, 12, 13)

    result = policy.resolve(
        origin_at=datetime(
            2026,
            8,
            9,
            12,
            0,
            tzinfo=BERLIN,
        ),
        window=HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=3,
        ),
        as_of=datetime(
            2026,
            8,
            12,
            17,
            30,
            tzinfo=BERLIN,
        ),
    )

    assert result.counted_session_keys == (
        "XETRA:2026-08-10",
        "XETRA:2026-08-11",
        "XETRA:2026-08-12",
    )
    assert result.endpoint_session.session_date == date(
        2026,
        8,
        12,
    )


def test_not_mature_before_endpoint_session_close() -> None:
    policy = policy_with_sessions(10)

    result = policy.resolve(
        origin_at=datetime(
            2026,
            8,
            9,
            12,
            0,
            tzinfo=BERLIN,
        ),
        window=HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=1,
        ),
        as_of=datetime(
            2026,
            8,
            10,
            17,
            29,
            59,
            tzinfo=BERLIN,
        ),
    )

    assert result.is_mature is False


def test_mature_exactly_at_endpoint_session_close() -> None:
    policy = policy_with_sessions(10)

    result = policy.resolve(
        origin_at=datetime(
            2026,
            8,
            9,
            12,
            0,
            tzinfo=BERLIN,
        ),
        window=HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=1,
        ),
        as_of=datetime(
            2026,
            8,
            10,
            17,
            30,
            tzinfo=BERLIN,
        ),
    )

    assert result.is_mature is True


def test_insufficient_local_calendar_data_is_explicit_error() -> None:
    policy = policy_with_sessions(10)

    with pytest.raises(
        ValueError,
        match="does not contain enough sessions",
    ):
        policy.resolve(
            origin_at=datetime(
                2026,
                8,
                9,
                12,
                0,
                tzinfo=BERLIN,
            ),
            window=HistoricalObservationWindow(
                kind="TRADING_SESSIONS",
                value=2,
            ),
            as_of=datetime(
                2026,
                8,
                20,
                tzinfo=timezone.utc,
            ),
        )


def test_elapsed_days_is_not_accepted_by_session_policy() -> None:
    policy = policy_with_sessions(10)

    with pytest.raises(
        ValueError,
        match="not supported",
    ):
        policy.resolve(
            origin_at=datetime(
                2026,
                8,
                9,
                12,
                0,
                tzinfo=BERLIN,
            ),
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=1,
            ),
            as_of=datetime(
                2026,
                8,
                20,
                tzinfo=timezone.utc,
            ),
        )


def test_resolution_is_json_ready() -> None:
    policy = policy_with_sessions(10)

    result = policy.resolve(
        origin_at=datetime(
            2026,
            8,
            9,
            12,
            0,
            tzinfo=BERLIN,
        ),
        window=HistoricalObservationWindow(
            kind="TRADING_SESSIONS",
            value=1,
        ),
        as_of=datetime(
            2026,
            8,
            10,
            17,
            30,
            tzinfo=BERLIN,
        ),
    )

    data = result.to_dict()

    assert data["is_mature"] is True
    assert data["endpoint_session"]["session_key"] == (
        "XETRA:2026-08-10"
    )
    assert data["counted_session_keys"] == [
        "XETRA:2026-08-10",
    ]
