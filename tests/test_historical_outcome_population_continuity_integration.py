"""
Tests for archive-continuity integration into population completeness.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_archive_gap_assessment import (
    HistoricalArchiveGapAssessmentService,
)
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
            origin_snapshot_id=f"11111111-1111-4111-8111-{day:012d}",
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


def complete_gap_assessment():
    return HistoricalArchiveGapAssessmentService().assess(
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


def gaps_assessment():
    return HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(
            dt(1),
            dt(2),
            dt(3),
        ),
        observed_timestamps=(
            dt(1),
            dt(3),
        ),
    )


def test_without_gap_assessment_preserves_not_assessed() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(3),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(3),
    )

    assert assessment.status == "COVERED"
    assert assessment.internal_continuity_status == "NOT_ASSESSED"
    assert "no explicit archive gap assessment" in assessment.warning


def test_complete_gap_assessment_sets_internal_complete() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(2),
            result(3),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(3),
        archive_gap_assessment=complete_gap_assessment(),
    )

    assert assessment.status == "COVERED"
    assert assessment.internal_continuity_status == "COMPLETE"
    assert "no missing expected archive timestamps" in assessment.warning


def test_gap_assessment_sets_internal_gaps_without_changing_boundary_status() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(3),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(3),
        archive_gap_assessment=gaps_assessment(),
    )

    assert assessment.status == "COVERED"
    assert assessment.internal_continuity_status == "GAPS"
    assert "missing expected archive timestamps" in assessment.warning


def test_boundary_partial_and_internal_complete_remain_distinct() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(2),
            result(3),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(3),
        archive_gap_assessment=complete_gap_assessment(),
    )

    assert assessment.status == "PARTIAL"
    assert assessment.internal_continuity_status == "COMPLETE"


def test_no_expectation_maps_to_not_assessed() -> None:
    no_expectation = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(),
        observed_timestamps=(
            dt(1),
        ),
    )

    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(1),
        archive_gap_assessment=no_expectation,
    )

    assert assessment.internal_continuity_status == "NOT_ASSESSED"


def test_serialization_exposes_internal_continuity_status() -> None:
    data = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(3),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(3),
        archive_gap_assessment=gaps_assessment(),
    ).to_dict()

    assert data["status"] == "COVERED"
    assert data["internal_continuity_status"] == "GAPS"


def test_invalid_gap_assessment_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="archive_gap_assessment must be",
    ):
        HistoricalOutcomePopulationCompletenessService().assess(
            (
                result(1),
            ),
            archive_gap_assessment=object(),  # type: ignore[arg-type]
        )
