"""
Focused tests for population metadata integration into research orchestration.
"""

from datetime import datetime, timedelta, timezone

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


def test_research_result_carries_unfiltered_population_metadata() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            complete_result(),
        ),
        protocol=protocol(),
    )

    population = output[0].population

    assert population.candidate_count == 1
    assert population.prefiltered is False
    assert population.selection_basis == "ARCHIVED_OBSERVATIONS"


def test_research_result_carries_explicit_query_selection_metadata() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            complete_result(),
        ),
        protocol=protocol(),
        population_query=HistoricalOutcomeQuery(
            recommendation_key="WORLD",
            action="BUY",
        ),
    )

    population = output[0].population

    assert population.prefiltered is True
    assert population.requested_recommendation_key == "WORLD"
    assert population.requested_action == "BUY"
    assert len(population.warnings) == 2


def test_population_metadata_is_in_json_ready_result() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(
            complete_result(),
        ),
        protocol=protocol(),
        population_query=HistoricalOutcomeQuery(
            symbol="IWDA",
        ),
    )

    data = output[0].to_dict()

    assert data["population"]["candidate_count"] == 1
    assert data["population"]["requested_symbol"] == "IWDA"
    assert data["population"]["prefiltered"] is True
