"""
Tests for exact historical archive gap assessment.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_archive_gap_assessment import (
    HistoricalArchiveGapAssessmentService,
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


def test_complete_when_all_expected_points_are_observed() -> None:
    assessment = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(
            dt(1),
            dt(2),
            dt(3),
        ),
        observed_timestamps=(
            dt(1),
            dt(2),
            dt(3),
        ),
    )

    assert assessment.status == "COMPLETE"
    assert assessment.expected_count == 3
    assert assessment.observed_expected_count == 3
    assert assessment.missing_count == 0
    assert assessment.unexpected_observed_count == 0
    assert assessment.expected_coverage_fraction == 1.0


def test_missing_expected_points_are_reported_exactly() -> None:
    assessment = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(
            dt(1),
            dt(2),
            dt(3),
            dt(4),
        ),
        observed_timestamps=(
            dt(1),
            dt(3),
        ),
    )

    assert assessment.status == "GAPS"
    assert assessment.expected_count == 4
    assert assessment.observed_expected_count == 2
    assert assessment.missing_count == 2
    assert assessment.missing_timestamps == (
        dt(2),
        dt(4),
    )
    assert assessment.expected_coverage_fraction == pytest.approx(
        0.5
    )


def test_unexpected_observed_points_are_separate_from_missing() -> None:
    assessment = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(
            dt(1),
            dt(2),
            dt(3),
        ),
        observed_timestamps=(
            dt(1),
            dt(2),
            dt(3),
            dt(
                2,
                13,
            ),
        ),
    )

    assert assessment.status == "COMPLETE"
    assert assessment.missing_count == 0
    assert assessment.unexpected_observed_count == 1
    assert assessment.unexpected_observed_timestamps == (
        dt(
            2,
            13,
        ),
    )


def test_missing_and_unexpected_can_exist_together() -> None:
    assessment = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(
            dt(1),
            dt(2),
            dt(3),
        ),
        observed_timestamps=(
            dt(1),
            dt(
                2,
                13,
            ),
        ),
    )

    assert assessment.status == "GAPS"
    assert assessment.observed_expected_count == 1
    assert assessment.missing_timestamps == (
        dt(2),
        dt(3),
    )
    assert assessment.unexpected_observed_timestamps == (
        dt(
            2,
            13,
        ),
    )


def test_no_expected_points_is_explicit_no_expectation() -> None:
    assessment = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(),
        observed_timestamps=(
            dt(1),
            dt(2),
        ),
    )

    assert assessment.status == "NO_EXPECTATION"
    assert assessment.expected_count == 0
    assert assessment.observed_expected_count == 0
    assert assessment.missing_count == 0
    assert assessment.expected_coverage_fraction is None
    assert assessment.unexpected_observed_count == 2


def test_duplicate_inputs_are_deduplicated() -> None:
    assessment = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(
            dt(1),
            dt(1),
            dt(2),
        ),
        observed_timestamps=(
            dt(1),
            dt(1),
        ),
    )

    assert assessment.expected_count == 2
    assert assessment.observed_expected_count == 1
    assert assessment.missing_count == 1
    assert assessment.missing_timestamps == (
        dt(2),
    )


def test_serialization_is_stable_and_sorted() -> None:
    data = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(
            dt(3),
            dt(1),
            dt(2),
        ),
        observed_timestamps=(
            dt(
                4,
                13,
            ),
            dt(1),
        ),
    ).to_dict()

    assert data["status"] == "GAPS"
    assert data["expected_count"] == 3
    assert data["observed_expected_count"] == 1
    assert data["missing_count"] == 2
    assert data["missing_timestamps"] == [
        dt(2).isoformat(),
        dt(3).isoformat(),
    ]
    assert data["unexpected_observed_timestamps"] == [
        dt(
            4,
            13,
        ).isoformat(),
    ]


def test_naive_expected_timestamp_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="expected_timestamps must be timezone-aware",
    ):
        HistoricalArchiveGapAssessmentService().assess(
            expected_timestamps=(
                datetime(
                    2026,
                    8,
                    1,
                    12,
                    0,
                ),
            ),
            observed_timestamps=(),
        )


def test_naive_observed_timestamp_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="observed_timestamps must be timezone-aware",
    ):
        HistoricalArchiveGapAssessmentService().assess(
            expected_timestamps=(),
            observed_timestamps=(
                datetime(
                    2026,
                    8,
                    1,
                    12,
                    0,
                ),
            ),
        )


def test_non_datetime_value_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="observed_timestamps must contain only datetime values",
    ):
        HistoricalArchiveGapAssessmentService().assess(
            expected_timestamps=(),
            observed_timestamps=(
                "2026-08-01T12:00:00+00:00",  # type: ignore[arg-type]
            ),
        )
