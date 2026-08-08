"""
Tests for the deterministic local market-session calendar boundary.
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


BERLIN = ZoneInfo(
    "Europe/Berlin"
)


def identity(
    *,
    calendar_id: str = "XETRA",
) -> HistoricalSessionCalendarIdentity:
    return HistoricalSessionCalendarIdentity(
        calendar_id=calendar_id,
        version=1,
        timezone="Europe/Berlin",
        source="LOCAL_SESSION_FIXTURE",
    )


def session(
    day: int,
    *,
    calendar: HistoricalSessionCalendarIdentity | None = None,
) -> HistoricalMarketSession:
    calendar = (
        identity()
        if calendar is None
        else calendar
    )
    return HistoricalMarketSession(
        session_key=f"{calendar.calendar_id}:2026-08-{day:02d}",
        session_date=date(
            2026,
            8,
            day,
        ),
        opens_at=datetime(
            2026,
            8,
            day,
            9,
            0,
            tzinfo=BERLIN,
        ),
        closes_at=datetime(
            2026,
            8,
            day,
            17,
            30,
            tzinfo=BERLIN,
        ),
        calendar=calendar,
    )


def test_calendar_orders_explicit_sessions_deterministically() -> None:
    cal = identity()
    provider = HistoricalLocalSessionCalendar(
        identity=cal,
        sessions=(
            session(
                11,
                calendar=cal,
            ),
            session(
                8,
                calendar=cal,
            ),
            session(
                10,
                calendar=cal,
            ),
        ),
    )

    assert [
        item.session_date
        for item in provider.list_all()
    ] == [
        date(
            2026,
            8,
            8,
        ),
        date(
            2026,
            8,
            10,
        ),
        date(
            2026,
            8,
            11,
        ),
    ]


def test_calendar_does_not_infer_missing_weekend_or_weekday_sessions() -> None:
    cal = identity()
    provider = HistoricalLocalSessionCalendar(
        identity=cal,
        sessions=(
            session(
                7,
                calendar=cal,
            ),
            session(
                10,
                calendar=cal,
            ),
        ),
    )

    assert provider.get_by_date(
        date(
            2026,
            8,
            8,
        )
    ) is None
    assert provider.get_by_date(
        date(
            2026,
            8,
            9,
        )
    ) is None


def test_get_by_key_and_date_are_exact_queries() -> None:
    cal = identity()
    august_10 = session(
        10,
        calendar=cal,
    )
    provider = HistoricalLocalSessionCalendar(
        identity=cal,
        sessions=(
            august_10,
        ),
    )

    assert provider.get_by_key(
        "XETRA:2026-08-10"
    ) == august_10
    assert provider.get_by_key(
        "XETRA:2026-08-11"
    ) is None
    assert provider.get_by_date(
        date(
            2026,
            8,
            10,
        )
    ) == august_10


def test_first_session_opening_after_requires_explicit_inclusion_rule() -> None:
    cal = identity()
    august_10 = session(
        10,
        calendar=cal,
    )
    august_11 = session(
        11,
        calendar=cal,
    )
    provider = HistoricalLocalSessionCalendar(
        identity=cal,
        sessions=(
            august_10,
            august_11,
        ),
    )

    assert provider.first_session_opening_after(
        august_10.opens_at,
        inclusive=False,
    ) == august_11
    assert provider.first_session_opening_after(
        august_10.opens_at,
        inclusive=True,
    ) == august_10


def test_sessions_after_returns_only_explicit_sessions() -> None:
    cal = identity()
    provider = HistoricalLocalSessionCalendar(
        identity=cal,
        sessions=(
            session(
                7,
                calendar=cal,
            ),
            session(
                10,
                calendar=cal,
            ),
            session(
                11,
                calendar=cal,
            ),
        ),
    )

    result = provider.sessions_after(
        datetime(
            2026,
            8,
            7,
            18,
            0,
            tzinfo=BERLIN,
        )
    )

    assert [
        item.session_date
        for item in result
    ] == [
        date(
            2026,
            8,
            10,
        ),
        date(
            2026,
            8,
            11,
        ),
    ]


def test_list_between_uses_explicit_session_open_timestamp() -> None:
    cal = identity()
    provider = HistoricalLocalSessionCalendar(
        identity=cal,
        sessions=(
            session(
                10,
                calendar=cal,
            ),
            session(
                11,
                calendar=cal,
            ),
            session(
                12,
                calendar=cal,
            ),
        ),
    )

    result = provider.list_between(
        start_at=datetime(
            2026,
            8,
            10,
            7,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2026,
            8,
            11,
            7,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert [
        item.session_date
        for item in result
    ] == [
        date(
            2026,
            8,
            10,
        ),
        date(
            2026,
            8,
            11,
        ),
    ]


def test_provider_rejects_mixed_calendar_identity() -> None:
    xetra = identity(
        calendar_id="XETRA"
    )
    nyse = HistoricalSessionCalendarIdentity(
        calendar_id="NYSE",
        version=1,
        timezone="America/New_York",
        source="LOCAL_SESSION_FIXTURE",
    )

    with pytest.raises(
        ValueError,
        match="calendar must match",
    ):
        HistoricalLocalSessionCalendar(
            identity=xetra,
            sessions=(
                session(
                    10,
                    calendar=nyse,
                ),
            ),
        )


def test_provider_rejects_duplicate_session_dates() -> None:
    cal = identity()
    first = session(
        10,
        calendar=cal,
    )
    duplicate_date = HistoricalMarketSession(
        session_key="XETRA:SPECIAL-2026-08-10",
        session_date=date(
            2026,
            8,
            10,
        ),
        opens_at=datetime(
            2026,
            8,
            10,
            10,
            0,
            tzinfo=BERLIN,
        ),
        closes_at=datetime(
            2026,
            8,
            10,
            18,
            0,
            tzinfo=BERLIN,
        ),
        calendar=cal,
    )

    with pytest.raises(
        ValueError,
        match="session_date values must be unique",
    ):
        HistoricalLocalSessionCalendar(
            identity=cal,
            sessions=(
                first,
                duplicate_date,
            ),
        )


def test_empty_calendar_is_valid_and_returns_no_sessions() -> None:
    provider = HistoricalLocalSessionCalendar(
        identity=identity(),
        sessions=(),
    )

    assert provider.list_all() == ()
    assert provider.first_session_opening_after(
        datetime(
            2026,
            8,
            10,
            tzinfo=timezone.utc,
        )
    ) is None
