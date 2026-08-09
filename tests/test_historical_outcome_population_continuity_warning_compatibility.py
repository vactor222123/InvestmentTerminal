"""
Backward-compatibility test for unassessed continuity warning wording.
"""

from datetime import datetime, timezone

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


def test_unassessed_warning_keeps_legacy_cadence_phrase() -> None:
    assessment = HistoricalOutcomePopulationCompletenessService().assess(
        (
            result(1),
            result(10),
        ),
        requested_origin_start=dt(1),
        requested_origin_end=dt(10),
    )

    assert assessment.internal_continuity_status == "NOT_ASSESSED"
    assert "no canonical expected snapshot cadence" in assessment.warning
    assert "no explicit archive gap assessment" in assessment.warning
