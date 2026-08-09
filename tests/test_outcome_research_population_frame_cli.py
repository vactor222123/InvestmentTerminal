"""
Tests for CLI population-frame integration.
"""

from unittest.mock import Mock

import pytest

from investment_terminal.cli.outcome_research import (
    _print_human,
)
from investment_terminal.history.historical_outcome_research_population_frame import (
    HistoricalOutcomeResearchPopulationFrameService,
)


def test_cli_frame_uses_produced_as_source_denominator() -> None:
    frame = HistoricalOutcomeResearchPopulationFrameService().build(
        source_observation_count=10,
        selected_candidate_count=3,
    )

    assert frame.source_observation_count == 10
    assert frame.selected_candidate_count == 3
    assert frame.excluded_by_selection_count == 7
    assert frame.selection_fraction == pytest.approx(0.3)


def test_human_output_exposes_selection_frame(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {
        "recommendation_key": "WORLD",
        "protocol": {
            "identity_key": "DESCRIPTIVE_OUTCOME_RESEARCH@1",
        },
        "methodology": {
            "identity_key": "ELAPSED_DAYS_EXACT_CLOSE@1",
        },
        "window": {
            "kind": "ELAPSED_DAYS",
            "value": 5,
        },
        "as_of": "2026-08-09T12:00:00+00:00",
        "resolution": "D",
        "candidate_count": 2,
        "produced_observation_count": 5,
        "cohort_count": 1,
        "cohorts": [
            {
                "cohort": {
                    "identity_key": "cohort-1",
                },
                "population_frame": {
                    "frame_basis": (
                        "ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS"
                    ),
                    "source_observation_count": 5,
                    "selected_candidate_count": 2,
                    "excluded_by_selection_count": 3,
                    "selection_fraction": 0.4,
                    "selection_applied": True,
                },
                "population": {
                    "selection_basis": "ARCHIVED_OBSERVATIONS",
                    "prefiltered": True,
                    "warnings": [
                        "archived sample warning",
                    ],
                },
                "coverage": {
                    "eligible_count": 1,
                    "candidate_count": 2,
                    "coverage_fraction": 0.5,
                    "complete_count": 1,
                    "partial_count": 1,
                    "unavailable_count": 0,
                    "not_mature_count": 0,
                },
                "sample_assessment": {
                    "status": "INSUFFICIENT",
                    "eligible_sample_size": 1,
                    "minimum_required_sample_size": 3,
                    "shortfall": 2,
                },
                "descriptive_summary": {
                    "mean_price_change_fraction": 0.05,
                    "median_price_change_fraction": 0.05,
                    "count": 1,
                },
                "uncertainty": {
                    "standard_error_of_mean": None,
                    "warning": "one observation",
                },
                "claim_assessment": {
                    "claim_policy": "DESCRIPTIVE_ONLY",
                    "sample_status": "INSUFFICIENT",
                    "warning": "insufficient sample",
                },
            }
        ],
    }

    _print_human(
        report
    )
    output = capsys.readouterr().out

    assert "Frame        : 2/5 selected (40.00%); excluded=3" in output
    assert "Coverage     : 1/2 eligible (50.00%)" in output
    assert "INSUFFICIENT" in output


def test_domain_frame_is_single_source_of_selection_arithmetic() -> None:
    service = Mock()
    service.build.return_value = (
        HistoricalOutcomeResearchPopulationFrameService().build(
            source_observation_count=7,
            selected_candidate_count=4,
        )
    )

    frame = service.build(
        source_observation_count=7,
        selected_candidate_count=4,
    )

    service.build.assert_called_once_with(
        source_observation_count=7,
        selected_candidate_count=4,
    )
    assert frame.excluded_by_selection_count == 3
