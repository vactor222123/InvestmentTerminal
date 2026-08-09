"""
Tests for the statistically honest historical outcome research CLI.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.outcome_research import (
    build_argument_parser,
    _print_human,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)


def test_parser_requires_minimum_sample_size() -> None:
    parser = build_argument_parser()

    with pytest.raises(
        SystemExit,
    ):
        parser.parse_args(
            [
                "--recommendation-key",
                "WORLD",
                "--methodology",
                "ELAPSED_DAYS_EXACT_CLOSE",
                "--window-value",
                "5",
                "--as-of",
                "2026-08-09T12:00:00+00:00",
            ]
        )


def test_parser_rejects_non_positive_minimum_sample_size() -> None:
    parser = build_argument_parser()

    with pytest.raises(
        SystemExit,
    ):
        parser.parse_args(
            [
                "--recommendation-key",
                "WORLD",
                "--methodology",
                "ELAPSED_DAYS_EXACT_CLOSE",
                "--window-value",
                "5",
                "--minimum-sample-size",
                "0",
                "--as-of",
                "2026-08-09T12:00:00+00:00",
            ]
        )


def test_cli_research_contract_can_be_built_from_arguments() -> None:
    methodology = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
    query = HistoricalOutcomeQuery(
        recommendation_key="WORLD",
        symbol="IWDA",
        action="BUY",
        window_kind="ELAPSED_DAYS",
        window_value=5,
        methodology_id=methodology.methodology_id,
        methodology_version=methodology.version,
    )
    protocol = HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            methodology.identity_key,
        ),
        minimum_complete_sample_size=10,
    )

    assert protocol.identity_key == "DESCRIPTIVE_OUTCOME_RESEARCH@1"
    assert query.recommendation_key == "WORLD"
    assert query.symbol == "IWDA"
    assert query.action == "BUY"
    assert query.methodology_version == 1


def test_json_ready_report_shape_preserves_research_semantics() -> None:
    methodology = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
    protocol = HistoricalOutcomeResearchProtocol.descriptive_v1(
        allowed_methodology_identities=(
            methodology.identity_key,
        ),
        minimum_complete_sample_size=3,
    )
    query = HistoricalOutcomeQuery(
        recommendation_key="WORLD",
        window_kind="ELAPSED_DAYS",
        window_value=5,
        methodology_id=methodology.methodology_id,
        methodology_version=methodology.version,
    )

    report = {
        "command": "historical_outcome_research",
        "protocol": protocol.to_dict(),
        "recommendation_key": "WORLD",
        "methodology": methodology.to_dict(),
        "window": {
            "kind": "ELAPSED_DAYS",
            "value": 5,
        },
        "session_calendar": None,
        "as_of": "2026-08-09T12:00:00+00:00",
        "resolution": "D",
        "query": query.to_dict(),
        "produced_observation_count": 4,
        "candidate_count": 3,
        "cohort_count": 1,
        "cohorts": [
            {
                "protocol_identity": "DESCRIPTIVE_OUTCOME_RESEARCH@1",
                "population_frame": {
                    "frame_basis": (
                        "ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS"
                    ),
                    "source_observation_count": 4,
                    "selected_candidate_count": 3,
                    "excluded_by_selection_count": 1,
                    "selection_fraction": 0.75,
                    "selection_applied": True,
                },
                "population": {
                    "selection_basis": "ARCHIVED_OBSERVATIONS",
                    "candidate_count": 3,
                    "prefiltered": True,
                    "warnings": [
                        "archived population warning",
                    ],
                },
                "cohort": {
                    "identity_key": "cohort",
                },
                "coverage": {
                    "candidate_count": 3,
                    "eligible_count": 2,
                    "complete_count": 2,
                    "partial_count": 1,
                    "unavailable_count": 0,
                    "not_mature_count": 0,
                    "excluded_count": 1,
                    "coverage_fraction": 2 / 3,
                },
                "sample_assessment": {
                    "status": "INSUFFICIENT",
                    "eligible_sample_size": 2,
                    "minimum_required_sample_size": 3,
                    "shortfall": 1,
                },
                "descriptive_summary": {
                    "count": 2,
                    "mean_price_change_fraction": 0.01,
                    "median_price_change_fraction": 0.01,
                },
                "uncertainty": {
                    "standard_error_of_mean": 0.005,
                    "warning": "no confidence interval",
                },
                "claim_assessment": {
                    "claim_policy": "DESCRIPTIVE_ONLY",
                    "sample_status": "INSUFFICIENT",
                    "warning": "insufficient sample",
                },
            }
        ],
    }

    encoded = json.dumps(
        report,
        allow_nan=False,
    )
    decoded = json.loads(
        encoded
    )

    assert decoded["protocol"]["identity_key"] == (
        "DESCRIPTIVE_OUTCOME_RESEARCH@1"
    )
    assert decoded["cohorts"][0]["population_frame"][
        "source_observation_count"
    ] == 4
    assert decoded["cohorts"][0]["population_frame"][
        "selected_candidate_count"
    ] == 3
    assert decoded["cohorts"][0]["sample_assessment"]["status"] == (
        "INSUFFICIENT"
    )
    assert decoded["cohorts"][0]["claim_assessment"]["claim_policy"] == (
        "DESCRIPTIVE_ONLY"
    )


def test_human_output_exposes_claim_and_population_warnings(
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
        "produced_observation_count": 3,
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
                    "source_observation_count": 3,
                    "selected_candidate_count": 2,
                    "excluded_by_selection_count": 1,
                    "selection_fraction": 2 / 3,
                    "selection_applied": True,
                },
                "population": {
                    "selection_basis": "ARCHIVED_OBSERVATIONS",
                    "prefiltered": True,
                    "warnings": [
                        "archived sample is not representative",
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

    assert "DESCRIPTIVE_OUTCOME_RESEARCH@1" in output
    assert "Frame        : 2/3 selected" in output
    assert "INSUFFICIENT" in output
    assert "DESCRIPTIVE_ONLY" in output
    assert "insufficient sample" in output
    assert "archived sample is not representative" in output


def test_cli_module_has_no_persistence_specific_arguments() -> None:
    parser = build_argument_parser()
    destinations = {
        action.dest
        for action in parser._actions
    }

    assert "persist" not in destinations
    assert "output_database" not in destinations
    assert "write_history" not in destinations
