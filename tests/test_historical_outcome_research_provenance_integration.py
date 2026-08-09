"""
Tests for canonical provenance-summary integration in research results and CLI.
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
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
)
from investment_terminal.history.historical_outcome_source_import_quality import (
    HistoricalOutcomeSourceImportQualityAssessment,
)


NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def result(number: int) -> HistoricalMethodologyAwareObservationResult:
    return HistoricalMethodologyAwareObservationResult(
        methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id=f"11111111-1111-4111-8111-{number:012d}",
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            origin_at=NOW,
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


def import_quality() -> HistoricalOutcomeSourceImportQualityAssessment:
    return HistoricalOutcomeSourceImportQualityAssessment(
        status="COMPLETE",
        source_observation_count=2,
        unique_snapshot_count=2,
        imported_snapshot_count=2,
        non_imported_snapshot_count=0,
        missing_state_snapshot_count=0,
        status_counts=(("IMPORTED", 2),),
        warning=None,
    )


def test_research_result_uses_single_provenance_envelope() -> None:
    source = (
        result(1),
        result(2),
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        source_results=source,
        source_import_quality=import_quality(),
    )

    cohort = output[0]
    assert cohort.provenance.complete_component_set is True
    assert cohort.provenance.population_frame.source_observation_count == 2
    assert cohort.provenance.selection_accounting is not None
    assert cohort.provenance.population_completeness is not None
    assert cohort.provenance.source_import_quality is not None


def test_serialization_uses_provenance_with_transitional_legacy_aliases() -> None:
    source = (
        result(1),
        result(2),
    )

    data = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        source_results=source,
        source_import_quality=import_quality(),
    )[0].to_dict()

    provenance = data["provenance"]
    assert provenance["complete_component_set"] is True
    assert provenance["population_frame"]["source_observation_count"] == 2
    assert provenance["source_import_quality"]["status"] == "COMPLETE"

    assert data["population_frame"] == provenance["population_frame"]
    assert data["selection_accounting"] == provenance["selection_accounting"]
    assert data["population_completeness"] == provenance["population_completeness"]
    assert data["source_import_quality"] == provenance["source_import_quality"]


def test_partial_caller_provenance_remains_explicitly_partial() -> None:
    source = (
        result(1),
    )

    cohort = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
    )[0]

    assert cohort.provenance.complete_component_set is False
    assert cohort.provenance.available_components == (
        "POPULATION_FRAME",
    )
    assert cohort.provenance.missing_components == (
        "SOURCE_IMPORT_QUALITY",
        "POPULATION_COMPLETENESS",
        "SELECTION_ACCOUNTING",
    )


def test_human_output_reads_only_provenance_envelope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {
        "recommendation_key": "WORLD",
        "protocol": {"identity_key": "DESCRIPTIVE_OUTCOME_RESEARCH@1"},
        "methodology": {"identity_key": "ELAPSED_DAYS_EXACT_CLOSE@1"},
        "window": {"kind": "ELAPSED_DAYS", "value": 5},
        "as_of": NOW.isoformat(),
        "resolution": "D",
        "candidate_count": 1,
        "produced_observation_count": 2,
        "cohort_count": 1,
        "cohorts": [
            {
                "cohort": {"identity_key": "cohort-1"},
                "provenance": {
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
                        ],
                        "total_reason_failures": 1,
                        "reason_counts_are_exclusive": False,
                    },
                    "population_completeness": {
                        "status": "UNKNOWN",
                        "source_observation_count": 2,
                        "observed_origin_start": NOW.isoformat(),
                        "observed_origin_end": NOW.isoformat(),
                        "requested_origin_start": None,
                        "requested_origin_end": None,
                        "covers_requested_start": None,
                        "covers_requested_end": None,
                        "internal_continuity_status": "NOT_ASSESSED",
                        "warning": "temporal boundary warning",
                    },
                    "source_import_quality": {
                        "status": "COMPLETE",
                        "source_observation_count": 2,
                        "unique_snapshot_count": 2,
                        "imported_snapshot_count": 2,
                        "non_imported_snapshot_count": 0,
                        "missing_state_snapshot_count": 0,
                        "imported_fraction": 1.0,
                        "status_counts": {"IMPORTED": 2},
                        "warning": None,
                    },
                    "available_components": [
                        "SOURCE_IMPORT_QUALITY",
                        "POPULATION_COMPLETENESS",
                        "POPULATION_FRAME",
                        "SELECTION_ACCOUNTING",
                    ],
                    "missing_components": [],
                    "complete_component_set": True,
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

    assert "Provenance   : 4/4 components; complete=True" in output
    assert "Import       : COMPLETE / 2/2 imported (100.00%)" in output
    assert "Frame        : 1/2 selected (50.00%); excluded=1" in output
    assert "Selection    : SYMBOL=1; reason_failures=1" in output
    assert "Completeness : UNKNOWN / internal=NOT_ASSESSED" in output
