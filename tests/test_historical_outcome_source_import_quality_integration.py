"""
Tests for source import quality integration into research results and CLI.
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


def quality(
    *,
    source_count: int,
    unique_count: int,
    imported_count: int,
    non_imported_count: int,
    missing_count: int,
    status: str,
) -> HistoricalOutcomeSourceImportQualityAssessment:
    status_counts = ()
    if imported_count:
        status_counts += (("IMPORTED", imported_count),)
    if non_imported_count:
        status_counts += (("METADATA_ONLY", non_imported_count),)

    return HistoricalOutcomeSourceImportQualityAssessment(
        status=status,
        source_observation_count=source_count,
        unique_snapshot_count=unique_count,
        imported_snapshot_count=imported_count,
        non_imported_snapshot_count=non_imported_count,
        missing_state_snapshot_count=missing_count,
        status_counts=status_counts,
        warning=(
            None
            if status == "COMPLETE"
            else "import lifecycle warning"
        ),
    )


def test_research_result_carries_source_import_quality() -> None:
    source = (result(1), result(2))
    assessment = quality(
        source_count=2,
        unique_count=2,
        imported_count=1,
        non_imported_count=1,
        missing_count=0,
        status="PARTIAL",
    )

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        source_results=source,
        source_import_quality=assessment,
    )

    assert output[0].source_import_quality is assessment
    data = output[0].to_dict()["source_import_quality"]
    assert data is not None
    assert data["status"] == "PARTIAL"
    assert data["imported_snapshot_count"] == 1


def test_source_import_quality_is_optional_for_non_repository_callers() -> None:
    source = (result(1),)

    output = HistoricalOutcomeResearchService().analyze(
        results=source,
        protocol=protocol(),
        source_results=source,
    )

    assert output[0].source_import_quality is None
    assert output[0].to_dict()["source_import_quality"] is None


def test_import_quality_source_count_must_match_source_results() -> None:
    source = (result(1), result(2))
    assessment = quality(
        source_count=1,
        unique_count=1,
        imported_count=1,
        non_imported_count=0,
        missing_count=0,
        status="COMPLETE",
    )

    with pytest.raises(
        ValueError,
        match="must match len",
    ):
        HistoricalOutcomeResearchService().analyze(
            results=source,
            protocol=protocol(),
            source_results=source,
            source_import_quality=assessment,
        )


def test_import_quality_source_count_must_match_count_only_boundary() -> None:
    assessment = quality(
        source_count=3,
        unique_count=3,
        imported_count=3,
        non_imported_count=0,
        missing_count=0,
        status="COMPLETE",
    )

    with pytest.raises(
        ValueError,
        match="effective source population",
    ):
        HistoricalOutcomeResearchService().analyze(
            results=(result(1),),
            protocol=protocol(),
            source_observation_count=2,
            source_import_quality=assessment,
        )


def test_human_output_exposes_import_quality(
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
                "source_import_quality": {
                    "status": "PARTIAL",
                    "source_observation_count": 2,
                    "unique_snapshot_count": 2,
                    "imported_snapshot_count": 1,
                    "non_imported_snapshot_count": 1,
                    "missing_state_snapshot_count": 0,
                    "imported_fraction": 0.5,
                    "status_counts": {
                        "IMPORTED": 1,
                        "METADATA_ONLY": 1,
                    },
                    "warning": "import lifecycle warning",
                },
                "population_frame": {
                    "source_observation_count": 2,
                    "selected_candidate_count": 1,
                    "excluded_by_selection_count": 1,
                    "selection_fraction": 0.5,
                },
                "selection_accounting": None,
                "population_completeness": None,
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

    assert "Import       : PARTIAL / 1/2 imported (50.00%)" in output
    assert "I-warning    : import lifecycle warning" in output
