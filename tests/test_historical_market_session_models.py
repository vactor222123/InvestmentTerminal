"""
Tests for canonical historical market-session models.
"""

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
    HistoricalSessionCalendarIdentity,
)


def calendar() -> HistoricalSessionCalendarIdentity:
    return HistoricalSessionCalendarIdentity(
        calendar_id=" xetra ",
        version=1,
        timezone="Europe/Berlin",
        source=" local_session_fixture ",
    )


def test_calendar_identity_is_normalized_and_json_ready() -> None:
    identity = calendar()

    assert identity.calendar_id == "XETRA"
    assert identity.identity_key == "XETRA@1"
    assert identity.timezone == "Europe/Berlin"
    assert identity.source == "LOCAL_SESSION_FIXTURE"
    assert identity.to_dict() == {
        "calendar_id": "XETRA",
        "version": 1,
        "identity_key": "XETRA@1",
        "timezone": "Europe/Berlin",
        "source": "LOCAL_SESSION_FIXTURE",
    }


@pytest.mark.parametrize(
    "version",
    (
        0,
        -1,
        True,
        1.5,
        "1",
    ),
)
def test_calendar_identity_requires_positive_integer_version(
    version: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        HistoricalSessionCalendarIdentity(
            calendar_id="XETRA",
            version=version,  # type: ignore[arg-type]
            timezone="Europe/Berlin",
            source="LOCAL",
        )


def test_market_session_preserves_explicit_calendar_evidence() -> None:
    berlin = ZoneInfo(
        "Europe/Berlin"
    )
    session = HistoricalMarketSession(
        session_key="XETRA:2026-08-10",
        session_date=date(
            2026,
            8,
            10,
        ),
        opens_at=datetime(
            2026,
            8,
            10,
            9,
            0,
            tzinfo=berlin,
        ),
        closes_at=datetime(
            2026,
            8,
            10,
            17,
            30,
            tzinfo=berlin,
        ),
        calendar=calendar(),
    )

    assert session.session_key == "XETRA:2026-08-10"
    assert session.session_date == date(
        2026,
        8,
        10,
    )
    assert session.calendar.identity_key == "XETRA@1"
    assert session.to_dict()[
        "closes_at"
    ] == "2026-08-10T17:30:00+02:00"


def test_session_requires_timezone_aware_open_and_close() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        HistoricalMarketSession(
            session_key="XETRA:2026-08-10",
            session_date=date(
                2026,
                8,
                10,
            ),
            opens_at=datetime(
                2026,
                8,
                10,
                9,
                0,
            ),
            closes_at=datetime(
                2026,
                8,
                10,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            calendar=calendar(),
        )


def test_session_close_must_be_after_open() -> None:
    with pytest.raises(
        ValueError,
        match="later than opens_at",
    ):
        HistoricalMarketSession(
            session_key="XETRA:2026-08-10",
            session_date=date(
                2026,
                8,
                10,
            ),
            opens_at=datetime(
                2026,
                8,
                10,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            closes_at=datetime(
                2026,
                8,
                10,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            calendar=calendar(),
        )


def test_session_requires_date_not_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="session_date",
    ):
        HistoricalMarketSession(
            session_key="XETRA:2026-08-10",
            session_date=datetime(
                2026,
                8,
                10,
                tzinfo=timezone.utc,
            ),  # type: ignore[arg-type]
            opens_at=datetime(
                2026,
                8,
                10,
                9,
                0,
                tzinfo=timezone.utc,
            ),
            closes_at=datetime(
                2026,
                8,
                10,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            calendar=calendar(),
        )


def test_session_requires_typed_calendar() -> None:
    with pytest.raises(
        TypeError,
        match="calendar",
    ):
        HistoricalMarketSession(
            session_key="XETRA:2026-08-10",
            session_date=date(
                2026,
                8,
                10,
            ),
            opens_at=datetime(
                2026,
                8,
                10,
                9,
                0,
                tzinfo=timezone.utc,
            ),
            closes_at=datetime(
                2026,
                8,
                10,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            calendar="XETRA",  # type: ignore[arg-type]
        )


def test_ordering_key_is_deterministic() -> None:
    first = HistoricalMarketSession(
        session_key="XETRA:2026-08-10",
        session_date=date(
            2026,
            8,
            10,
        ),
        opens_at=datetime(
            2026,
            8,
            10,
            7,
            0,
            tzinfo=timezone.utc,
        ),
        closes_at=datetime(
            2026,
            8,
            10,
            15,
            30,
            tzinfo=timezone.utc,
        ),
        calendar=calendar(),
    )
    second = HistoricalMarketSession(
        session_key="XETRA:2026-08-11",
        session_date=date(
            2026,
            8,
            11,
        ),
        opens_at=datetime(
            2026,
            8,
            11,
            7,
            0,
            tzinfo=timezone.utc,
        ),
        closes_at=datetime(
            2026,
            8,
            11,
            15,
            30,
            tzinfo=timezone.utc,
        ),
        calendar=calendar(),
    )

    assert sorted(
        (
            second,
            first,
        ),
        key=lambda item: item.ordering_key,
    ) == [
        first,
        second,
    ]


def test_models_are_frozen() -> None:
    identity = calendar()

    with pytest.raises(
        FrozenInstanceError,
    ):
        identity.version = 2  # type: ignore[misc]
