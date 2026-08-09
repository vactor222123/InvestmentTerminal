"""
Tests for selection-accounting integration in research service and CLI.
"""

from datetime import datetime, timedelta, timezone

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


ORIGIN = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def partial_result(
    *,
    symbol: str = "IWDA",
    action: str = "BUY",
    origin_at: datetime = ORIGIN,
) -> HistoricalMethodologyAwareObservationResult:
    return HistoricalMethodologyAwareObservationResult(
        methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id="11111111-1111-4111-8111-111111111111",
            recommendation_key="WORLD",
            symbol=symbol,
            action=action,
            origin_at=origin_at,
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
        allowed_methodology_identities=(
            "ELAPSED_DAYS_EXACT_CLOSE@1",
        ),
        minimum_complete_sample_size=1,
    )


def test_research_result_carries_selection_accounting() -> None:
    selected = partial_result()
    rejected = partial_result(
        symbol="EIMI",
        action="HOLD",
    )
    query = HistoricalOutcomeQuery(
        recommendation_key="WORLD",
        symbol="IWDA",
        action="BUY",
        window_kind="ELAPSED_DAYS",
        window_value=5,
        methodology_id="ELAPSED_DAYS_EXACT_CLOSE",
        methodology_version=1,
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=(selected,),
        protocol=protocol(),
        population_query=query,
        source_results=(selected, rejected),
    )

    accounting = output[0].selection_accounting
    assert accounting is not None
    assert accounting.source_observation_count == 2
    assert accounting.selected_candidate_count == 1
    assert accounting.excluded_observation_count == 1
    assert {
        item.reason: item.count
        for item in accounting.reason_counts
    } == {
        "SYMBOL": 1,
        "ACTION": 1,
    }


def test_no_source_results_keeps_accounting_explicitly_unavailable() -> None:
    output = HistoricalOutcomeResearchService().analyze(
        results=(partial_result(),),
        protocol=protocol(),
    )

    assert output[0].selection_accounting is None
    assert output[0].to_dict()["selection_accounting"] is None


def test_source_results_must_reproduce_selected_count() -> None:
    source = (
        partial_result(symbol="EIMI"),
    )
    query = HistoricalOutcomeQuery(
        symbol="IWDA",
    )

    with pytest.raises(
        ValueError,
        match="same selected candidate count",
    ):
        HistoricalOutcomeResearchService().analyze(
            results=(partial_result(),),
            protocol=protocol(),
            population_query=query,
            source_results=source,
        )


def test_explicit_source_count_must_match_source_results() -> None:
    source = (
        partial_result(),
        partial_result(origin_at=ORIGIN + timedelta(days=1)),
    )

    with pytest.raises(
        ValueError,
        match="must match len",
    ):
        HistoricalOutcomeResearchService().analyze(
            results=source,
            protocol=protocol(),
            source_observation_count=3,
            source_results=source,
        )


def test_human_output_exposes_nonexclusive_reason_counts(
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
                "selection_accounting": {
                    "source_observation_count": 2,
                    "selected_candidate_count": 1,
                    "excluded_observation_count": 1,
                    "reason_counts": [
                        {"reason": "SYMBOL", "count": 1},
                        {"reason": "ACTION", "count": 1},
                    ],
                    "total_reason_failures": 2,
                    "reason_counts_are_exclusive": False,
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

    assert "Selection    : SYMBOL=1, ACTION=1; reason_failures=2" in output
    assert "Frame        : 1/2 selected (50.00%); excluded=1" in output
