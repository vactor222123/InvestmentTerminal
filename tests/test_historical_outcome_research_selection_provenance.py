"""
Tests for population-frame provenance in research orchestration.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
)


ORIGIN = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def complete_result() -> HistoricalMethodologyAwareObservationResult:
    methodology = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
    endpoint = ORIGIN + timedelta(days=5)
    evidence = HistoricalOutcomeEvidence(
        instrument_key="IWDA",
        origin_at=ORIGIN,
        endpoint_at=endpoint,
        origin_price=100.0,
        endpoint_price=105.0,
        origin_source="fixture",
        endpoint_source="fixture",
        origin_currency="EUR",
        endpoint_currency="EUR",
        origin_resolution="D",
        endpoint_resolution="D",
    )
    outcome = HistoricalRecommendationOutcome(
        instrument_key="IWDA",
        currency="EUR",
        origin_price=100.0,
        endpoint_price=105.0,
        price_change=5.0,
        price_change_fraction=(105.0 / 100.0) - 1.0,
        origin_source="fixture",
        endpoint_source="fixture",
    )
    return HistoricalMethodologyAwareObservationResult(
        methodology=methodology,
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id="11111111-1111-4111-8111-111111111111",
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=ORIGIN,
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=5,
            ),
            status="COMPLETE",
            evidence=evidence,
            warnings=(),
        ),
        outcome=outcome,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def protocol() -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            "ELAPSED_DAYS_EXACT_CLOSE@1",
        ),
        minimum_complete_sample_size=1,
    )


def test_explicit_source_denominator_is_carried_into_result() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            complete_result(),
        ),
        protocol=protocol(),
        population_query=HistoricalOutcomeQuery(
            recommendation_key="WORLD",
            action="BUY",
        ),
        source_observation_count=10,
    )

    frame = output[0].population_frame

    assert frame.source_observation_count == 10
    assert frame.selected_candidate_count == 1
    assert frame.excluded_by_selection_count == 9
    assert frame.selection_fraction == 0.1
    assert frame.selection_applied is True


def test_omitted_source_denominator_preserves_backward_compatibility() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            complete_result(),
        ),
        protocol=protocol(),
    )

    frame = output[0].population_frame

    assert frame.source_observation_count == 1
    assert frame.selected_candidate_count == 1
    assert frame.excluded_by_selection_count == 0
    assert frame.selection_applied is False


def test_json_ready_result_contains_selection_provenance() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            complete_result(),
        ),
        protocol=protocol(),
        source_observation_count=4,
    )

    data = output[0].to_dict()

    assert data["population_frame"] == {
        "frame_basis": "ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS",
        "source_observation_count": 4,
        "selected_candidate_count": 1,
        "excluded_by_selection_count": 3,
        "selection_fraction": 0.25,
        "selection_applied": True,
    }


def test_source_denominator_cannot_be_smaller_than_selected_results() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed",
    ):
        HistoricalOutcomeResearchService().analyze(
            results=(
                complete_result(),
            ),
            protocol=protocol(),
            source_observation_count=0,
        )


@pytest.mark.parametrize(
    "source_count",
    [
        -1,
        True,
        1.5,
    ],
)
def test_invalid_source_denominator_is_rejected(
    source_count: object,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        HistoricalOutcomeResearchService().analyze(
            results=(),
            protocol=protocol(),
            source_observation_count=source_count,  # type: ignore[arg-type]
        )
