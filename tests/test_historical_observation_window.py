"""
Tests for the canonical Sprint 14 observation-window policy.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
    HistoricalObservationWindowResolution,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
)


ORIGIN = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)


def test_elapsed_days_resolves_absolute_24_hour_periods() -> None:
    result = HistoricalObservationWindowPolicy().resolve(
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="elapsed_days",
            value=5,
        ),
        as_of=ORIGIN + timedelta(
            days=5
        ),
    )

    assert result.origin_at == ORIGIN
    assert result.endpoint_at == (
        ORIGIN
        + timedelta(
            days=5
        )
    )
    assert result.is_mature


def test_window_is_not_mature_before_endpoint() -> None:
    result = HistoricalObservationWindowPolicy().resolve(
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=20,
        ),
        as_of=ORIGIN + timedelta(
            days=19,
            hours=23,
            minutes=59,
        ),
    )

    assert not result.is_mature


def test_window_matures_exactly_at_endpoint() -> None:
    endpoint = ORIGIN + timedelta(
        days=1
    )

    result = HistoricalObservationWindowPolicy().resolve(
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=1,
        ),
        as_of=endpoint,
    )

    assert result.endpoint_at == endpoint
    assert result.is_mature


def test_policy_normalizes_origin_and_as_of_to_utc() -> None:
    berlin = ZoneInfo(
        "Europe/Berlin"
    )
    local_origin = datetime(
        2026,
        8,
        3,
        19,
        35,
        tzinfo=berlin,
    )
    local_as_of = datetime(
        2026,
        8,
        4,
        19,
        35,
        tzinfo=berlin,
    )

    result = HistoricalObservationWindowPolicy().resolve(
        origin_at=local_origin,
        window=HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=1,
        ),
        as_of=local_as_of,
    )

    assert result.origin_at == ORIGIN
    assert result.endpoint_at == (
        ORIGIN
        + timedelta(
            days=1
        )
    )
    assert result.as_of == (
        ORIGIN
        + timedelta(
            days=1
        )
    )
    assert result.is_mature


def test_policy_uses_absolute_duration_across_dst_transition() -> None:
    berlin = ZoneInfo(
        "Europe/Berlin"
    )
    origin = datetime(
        2026,
        10,
        24,
        12,
        0,
        tzinfo=berlin,
    )

    result = HistoricalObservationWindowPolicy().resolve(
        origin_at=origin,
        window=HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=1,
        ),
        as_of=origin.astimezone(
            timezone.utc
        )
        + timedelta(
            hours=24
        ),
    )

    assert (
        result.endpoint_at
        - result.origin_at
    ) == timedelta(
        hours=24
    )
    assert result.is_mature


@pytest.mark.parametrize(
    "kind",
    (
        "TRADING_SESSIONS",
        "CALENDAR_DAYS",
        "UNKNOWN",
    ),
)
def test_policy_rejects_unimplemented_window_kinds(
    kind: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="not supported",
    ):
        HistoricalObservationWindowPolicy().resolve(
            origin_at=ORIGIN,
            window=HistoricalObservationWindow(
                kind=kind,
                value=5,
            ),
            as_of=ORIGIN + timedelta(
                days=10
            ),
        )


def test_policy_rejects_naive_origin() -> None:
    with pytest.raises(
        ValueError,
        match="origin_at must be timezone-aware",
    ):
        HistoricalObservationWindowPolicy().resolve(
            origin_at=datetime(
                2026,
                8,
                3,
                17,
                35,
            ),
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=5,
            ),
            as_of=ORIGIN + timedelta(
                days=5
            ),
        )


def test_resolution_rejects_inconsistent_maturity_flag() -> None:
    with pytest.raises(
        ValueError,
        match="is_mature must match",
    ):
        HistoricalObservationWindowResolution(
            origin_at=ORIGIN,
            endpoint_at=ORIGIN + timedelta(
                days=5
            ),
            as_of=ORIGIN + timedelta(
                days=4
            ),
            is_mature=True,
        )


def test_resolution_is_json_ready() -> None:
    result = HistoricalObservationWindowPolicy().resolve(
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=5,
        ),
        as_of=ORIGIN + timedelta(
            days=6
        ),
    )

    assert result.to_dict() == {
        "origin_at": ORIGIN.isoformat(),
        "endpoint_at": (
            ORIGIN
            + timedelta(
                days=5
            )
        ).isoformat(),
        "as_of": (
            ORIGIN
            + timedelta(
                days=6
            )
        ).isoformat(),
        "is_mature": True,
    }
