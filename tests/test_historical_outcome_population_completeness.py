"""
Tests for temporal research-population completeness assessment.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_population_completeness import (
    HistoricalOutcomePopulationCompletenessService,
)


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def result(day: int) -> HistoricalMethodologyAwareObservationResult:
    return HistoricalMethodologyAwareObservationResult(
        methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id=(
                f"11111111-1111-4111-8111-{day:012d}"
            ),
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=dt(day),
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=5,
            ),
            status="PARTIAL",
            evidence=None,
            warnings=(),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def test_full_temporal_boundary_coverage_is_covered() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(5),
            result(10),
        ),
        requested_origin_start=dt(2),
        requested_origin_end=dt(9),
    )

    assert assessment.status == "COVERED"
    assert assessment.covers_requested_start is True
    assert assessment.covers_requested_end is True
    assert assessment.observed_origin_start == dt(1)
    assert assessment.observed_origin_end == dt(10)


def test_missing_left_boundary_is_partial() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(5),
            result(10),
        ),
        requested_origin_start=dt(2),
        requested_origin_end=dt(9),
    )

    assert assessment.status == "PARTIAL"
    assert assessment.covers_requested_start is False
    assert assessment.covers_requested_end is True


def test_missing_right_boundary_is_partial() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(5),
        ),
        requested_origin_start=dt(2),
        requested_origin_end=dt(9),
    )

    assert assessment.status == "PARTIAL"
    assert assessment.covers_requested_start is True
    assert assessment.covers_requested_end is False


def test_no_requested_range_is_unknown() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(10),
        ),
    )

    assert assessment.status == "UNKNOWN"
    assert assessment.covers_requested_start is None
    assert assessment.covers_requested_end is None


def test_empty_source_is_unknown_even_with_requested_range() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (),
        requested_origin_start=dt(2),
        requested_origin_end=dt(9),
    )

    assert assessment.status == "UNKNOWN"
    assert assessment.source_observation_count == 0
    assert assessment.observed_origin_start is None
    assert assessment.observed_origin_end is None


def test_one_sided_requested_boundary_can_be_covered() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(5),
        ),
        requested_origin_start=dt(2),
    )

    assert assessment.status == "COVERED"
    assert assessment.covers_requested_start is True
    assert assessment.covers_requested_end is None


def test_internal_continuity_is_never_inferred() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(10),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(10),
    )

    assert assessment.status == "COVERED"
    assert assessment.internal_continuity_status == "NOT_ASSESSED"
    assert "no canonical expected snapshot cadence" in assessment.warning


def test_serialization_is_explicit() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(10),
        ),
        requested_origin_start=dt(2),
        requested_origin_end=dt(9),
    )

    data = assessment.to_dict()

    assert data["status"] == "COVERED"
    assert data["source_observation_count"] == 2
    assert data["observed_origin_start"] == dt(1).isoformat()
    assert data["observed_origin_end"] == dt(10).isoformat()
    assert data["internal_continuity_status"] == "NOT_ASSESSED"


def test_invalid_requested_range_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must not be later",
    ):
        HistoricalOutcomePopulationCompletenessService().assess(
            (),
            requested_origin_start=dt(9),
            requested_origin_end=dt(2),
        )


def test_invalid_result_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="results must contain only",
    ):
        HistoricalOutcomePopulationCompletenessService().assess(
            (
                object(),  # type: ignore[arg-type]
            ),
        )
