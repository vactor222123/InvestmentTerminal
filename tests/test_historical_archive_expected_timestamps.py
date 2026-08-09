"""
Tests for deterministic expected archive timestamp generation.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_archive_cadence import (
    HistoricalArchiveCadencePolicy,
)
from investment_terminal.history.historical_archive_expected_timestamps import (
    HistoricalArchiveExpectedTimestampService,
)


def dt(
    day: int,
    hour: int = 12,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        0,
        tzinfo=timezone.utc,
    )


def daily_policy() -> HistoricalArchiveCadencePolicy:
    return HistoricalArchiveCadencePolicy.fixed_interval_v1(
        anchor_at=dt(1),
        interval_seconds=86_400,
    )


def test_generate_includes_aligned_start_and_end_boundaries() -> None:
    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=daily_policy(),
        start_at=dt(2),
        end_at=dt(4),
    )

    assert points == (
        dt(2),
        dt(3),
        dt(4),
    )


def test_generate_rounds_forward_to_next_cadence_point() -> None:
    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=daily_policy(),
        start_at=dt(
            2,
            13,
        ),
        end_at=dt(4),
    )

    assert points == (
        dt(3),
        dt(4),
    )


def test_generate_does_not_round_end_forward() -> None:
    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=daily_policy(),
        start_at=dt(2),
        end_at=dt(
            3,
            11,
        ),
    )

    assert points == (
        dt(2),
    )


def test_interval_before_anchor_has_no_expected_points() -> None:
    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=daily_policy(),
        start_at=datetime(
            2026,
            7,
            29,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=datetime(
            2026,
            7,
            31,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert points == ()


def test_interval_crossing_anchor_starts_at_anchor() -> None:
    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=daily_policy(),
        start_at=datetime(
            2026,
            7,
            31,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        end_at=dt(2),
    )

    assert points == (
        dt(1),
        dt(2),
    )


def test_single_aligned_point_is_returned() -> None:
    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=daily_policy(),
        start_at=dt(3),
        end_at=dt(3),
    )

    assert points == (
        dt(3),
    )


def test_single_unaligned_instant_returns_empty_tuple() -> None:
    instant = dt(
        3,
        13,
    )
    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=daily_policy(),
        start_at=instant,
        end_at=instant,
    )

    assert points == ()


def test_hourly_policy_is_supported_without_calendar_semantics() -> None:
    policy = HistoricalArchiveCadencePolicy.fixed_interval_v1(
        anchor_at=dt(1),
        interval_seconds=3_600,
    )

    points = HistoricalArchiveExpectedTimestampService().generate(
        policy=policy,
        start_at=dt(
            1,
            13,
        ),
        end_at=dt(
            1,
            15,
        ),
    )

    assert points == (
        dt(
            1,
            13,
        ),
        dt(
            1,
            14,
        ),
        dt(
            1,
            15,
        ),
    )


def test_rejects_inverted_interval() -> None:
    with pytest.raises(
        ValueError,
        match="start_at must not be later",
    ):
        HistoricalArchiveExpectedTimestampService().generate(
            policy=daily_policy(),
            start_at=dt(4),
            end_at=dt(2),
        )


def test_rejects_naive_start() -> None:
    with pytest.raises(
        ValueError,
        match="start_at must be timezone-aware",
    ):
        HistoricalArchiveExpectedTimestampService().generate(
            policy=daily_policy(),
            start_at=datetime(
                2026,
                8,
                2,
                12,
                0,
            ),
            end_at=dt(4),
        )


def test_rejects_naive_end() -> None:
    with pytest.raises(
        ValueError,
        match="end_at must be timezone-aware",
    ):
        HistoricalArchiveExpectedTimestampService().generate(
            policy=daily_policy(),
            start_at=dt(2),
            end_at=datetime(
                2026,
                8,
                4,
                12,
                0,
            ),
        )


def test_rejects_invalid_policy_type() -> None:
    with pytest.raises(
        TypeError,
        match="policy must be",
    ):
        HistoricalArchiveExpectedTimestampService().generate(
            policy=object(),  # type: ignore[arg-type]
            start_at=dt(2),
            end_at=dt(4),
        )
