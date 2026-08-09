"""
Tests for application/domain wiring of explicit archive continuity.
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
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
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


def protocol() -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=("ELAPSED_DAYS_EXACT_CLOSE@1",),
        minimum_complete_sample_size=1,
    )


def query() -> HistoricalOutcomeQuery:
    return HistoricalOutcomeQuery(
        recommendation_key="WORLD",
        window_kind="ELAPSED_DAYS",
        window_value=5,
        methodology_id="ELAPSED_DAYS_EXACT_CLOSE",
        methodology_version=1,
        origin_from=dt(1),
        origin_to=dt(3),
    )


def test_research_service_accepts_explicit_gap_assessment() -> None:
    source = (
        result(1),
        result(3),
    )
    gaps = HistoricalArchiveGapAssessmentService().assess(
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

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        population_query=query(),
        source_results=source,
        archive_gap_assessment=gaps,
    )

    completeness = output[0].provenance.population_completeness
    assert completeness is not None
    assert completeness.status == "COVERED"
    assert completeness.internal_continuity_status == "GAPS"


def test_research_service_preserves_not_assessed_without_gap_input() -> None:
    source = (
        result(1),
        result(3),
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        population_query=query(),
        source_results=source,
    )

    completeness = output[0].provenance.population_completeness
    assert completeness is not None
    assert completeness.internal_continuity_status == "NOT_ASSESSED"


def test_complete_gap_assessment_flows_into_provenance() -> None:
    source = (
        result(1),
        result(2),
        result(3),
    )
    complete = HistoricalArchiveGapAssessmentService().assess(
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

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        population_query=query(),
        source_results=source,
        archive_gap_assessment=complete,
    )

    payload = output[0].to_dict()
    assert payload["provenance"]["population_completeness"][
        "internal_continuity_status"
    ] == "COMPLETE"
    assert payload["population_completeness"][
        "internal_continuity_status"
    ] == "COMPLETE"


def test_invalid_gap_assessment_type_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="archive_gap_assessment must be",
    ):
        HistoricalOutcomeResearchService().analyze(
            results=(result(1),),
            protocol=protocol(),
            archive_gap_assessment=object(),  # type: ignore[arg-type]
        )
