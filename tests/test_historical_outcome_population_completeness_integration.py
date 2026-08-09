"""
Tests for population completeness integration into research results and CLI.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.cli.outcome_research import _print_human
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
from investment_terminal.history.historical_outcome_query import HistoricalOutcomeQuery
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
)


def dt(day: int) -> datetime:
    return datetime(2026, 8, day, 12, 0, tzinfo=timezone.utc)


def partial_result(day: int) -> HistoricalMethodologyAwareObservationResult:
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


def test_source_results_drive_temporal_completeness() -> None:
    source = (
        partial_result(1),
        partial_result(5),
        partial_result(10),
    )
    query = HistoricalOutcomeQuery(
        recommendation_key="WORLD",
        window_kind="ELAPSED_DAYS",
        window_value=5,
        methodology_id="ELAPSED_DAYS_EXACT_CLOSE",
        methodology_version=1,
        origin_from=dt(2),
        origin_to=dt(9),
    )

    selected = (
        source[1],
    )
    output = HistoricalOutcomeResearchService().analyze(
        results=selected,
        protocol=protocol(),
        population_query=query,
        source_results=source,
    )

    completeness = output[0].population_completeness
    assert completeness is not None
    assert completeness.status == "COVERED"
    assert completeness.observed_origin_start == dt(1)
    assert completeness.observed_origin_end == dt(10)
    assert completeness.requested_origin_start == dt(2)
    assert completeness.requested_origin_end == dt(9)
    assert completeness.internal_continuity_status == "NOT_ASSESSED"


def test_no_requested_time_range_is_unknown_not_complete() -> None:
    source = (
        partial_result(1),
        partial_result(10),
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        source_results=source,
    )

    completeness = output[0].population_completeness
    assert completeness is not None
    assert completeness.status == "UNKNOWN"
    assert completeness.covers_requested_start is None
    assert completeness.covers_requested_end is None


def test_without_source_results_completeness_is_unavailable() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(partial_result(5),),
        protocol=protocol(),
    )

    assert output[0].population_completeness is None
    assert output[0].to_dict()["population_completeness"] is None


def test_json_ready_result_contains_completeness() -> None:
    source = (
        partial_result(3),
        partial_result(8),
    )
    query = HistoricalOutcomeQuery(
        origin_from=dt(1),
        origin_to=dt(9),
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        population_query=query,
        source_results=source,
    )

    data = output[0].to_dict()["population_completeness"]
    assert data is not None
    assert data["status"] == "PARTIAL"
    assert data["covers_requested_start"] is False
    assert data["covers_requested_end"] is False
    assert data["internal_continuity_status"] == "NOT_ASSESSED"


def test_human_output_exposes_completeness_boundary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {
        "recommendation_key": "WORLD",
        "protocol": {"identity_key": "DESCRIPTIVE_OUTCOME_RESEARCH@1"},
        "methodology": {"identity_key": "ELAPSED_DAYS_EXACT_CLOSE@1"},
        "window": {"kind": "ELAPSED_DAYS", "value": 5},
        "as_of": "2026-08-09T12:00:00+00:00",
        "resolution": "D",
        "candidate_count": 1,
        "produced_observation_count": 2,
        "cohort_count": 1,
        "cohorts": [
            {
                "cohort": {"identity_key": "cohort-1"},
                "population_frame": {
                    "source_observation_count": 2,
                    "selected_candidate_count": 1,
                    "excluded_by_selection_count": 1,
                    "selection_fraction": 0.5,
                },
                "selection_accounting": None,
                "population_completeness": {
                    "status": "PARTIAL",
                    "source_observation_count": 2,
                    "observed_origin_start": dt(3).isoformat(),
                    "observed_origin_end": dt(8).isoformat(),
                    "requested_origin_start": dt(1).isoformat(),
                    "requested_origin_end": dt(9).isoformat(),
                    "covers_requested_start": False,
                    "covers_requested_end": False,
                    "internal_continuity_status": "NOT_ASSESSED",
                    "warning": "temporal boundary warning",
                },
                "population": {
                    "selection_basis": "ARCHIVED_OBSERVATIONS",
                    "prefiltered": True,
                    "warnings": ["archived sample warning"],
                },
                "coverage": {
                    "eligible_count": 0,
                    "candidate_count": 1,
                    "coverage_fraction": 0.0,
                    "complete_count": 0,
                    "partial_count": 1,
                    "unavailable_count": 0,
                    "not_mature_count": 0,
                },
                "sample_assessment": {
                    "status": "INSUFFICIENT",
                    "eligible_sample_size": 0,
                    "minimum_required_sample_size": 1,
                    "shortfall": 1,
                },
                "descriptive_summary": None,
                "uncertainty": None,
                "claim_assessment": {
                    "claim_policy": "DESCRIPTIVE_ONLY",
                    "sample_status": "INSUFFICIENT",
                    "warning": "insufficient",
                },
            }
        ],
    }

    _print_human(report)
    output = capsys.readouterr().out

    assert "Completeness : PARTIAL / internal=NOT_ASSESSED" in output
    assert "C-warning    : temporal boundary warning" in output
