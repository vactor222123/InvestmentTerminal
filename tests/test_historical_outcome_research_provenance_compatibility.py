"""
Compatibility tests for provenance-summary migration.
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


NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def result() -> HistoricalMethodologyAwareObservationResult:
    return HistoricalMethodologyAwareObservationResult(
        methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id="11111111-1111-4111-8111-111111111111",
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


def test_legacy_properties_delegate_to_provenance() -> None:
    source = (result(),)

    cohort = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        source_results=source,
    )[0]

    assert cohort.population_frame is cohort.provenance.population_frame
    assert (
        cohort.selection_accounting
        is cohort.provenance.selection_accounting
    )
    assert (
        cohort.population_completeness
        is cohort.provenance.population_completeness
    )
    assert (
        cohort.source_import_quality
        is cohort.provenance.source_import_quality
    )

    data = cohort.to_dict()
    assert "provenance" in data
    assert data["population_frame"] == data["provenance"]["population_frame"]
    assert (
        data["selection_accounting"]
        == data["provenance"]["selection_accounting"]
    )
    assert (
        data["population_completeness"]
        == data["provenance"]["population_completeness"]
    )
    assert (
        data["source_import_quality"]
        == data["provenance"]["source_import_quality"]
    )


def test_human_renderer_accepts_legacy_fixture_shape(
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
                "population_frame": {
                    "source_observation_count": 2,
                    "selected_candidate_count": 1,
                    "excluded_by_selection_count": 1,
                    "selection_fraction": 0.5,
                },
                "selection_accounting": None,
                "population_completeness": None,
                "source_import_quality": None,
                "population": {
                    "selection_basis": "ARCHIVED_OBSERVATIONS",
                    "prefiltered": True,
                    "warnings": [],
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

    assert "Provenance   : 1/4 components; complete=False" in output
    assert "Frame        : 1/2 selected (50.00%); excluded=1" in output
