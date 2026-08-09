"""
Tests for the immutable historical research provenance summary contract.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_outcome_population_completeness import (
    HistoricalOutcomePopulationCompletenessAssessment,
)
from investment_terminal.history.historical_outcome_research_population_frame import (
    HistoricalOutcomeResearchPopulationFrameService,
)
from investment_terminal.history.historical_outcome_research_provenance import (
    HistoricalOutcomeResearchProvenanceSummaryService,
)
from investment_terminal.history.historical_outcome_selection_accounting import (
    HistoricalOutcomeSelectionAccounting,
    HistoricalOutcomeSelectionReasonCount,
)
from investment_terminal.history.historical_outcome_source_import_quality import (
    HistoricalOutcomeSourceImportQualityAssessment,
)


NOW = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)


def frame(
    *,
    source: int = 10,
    selected: int = 4,
):
    return HistoricalOutcomeResearchPopulationFrameService().build(
        source_observation_count=source,
        selected_candidate_count=selected,
    )


def accounting(
    *,
    source: int = 10,
    selected: int = 4,
):
    return HistoricalOutcomeSelectionAccounting(
        source_observation_count=source,
        selected_candidate_count=selected,
        excluded_observation_count=source - selected,
        reason_counts=(
            HistoricalOutcomeSelectionReasonCount(
                reason="SYMBOL",
                count=source - selected,
            ),
        ),
    )


def completeness(
    *,
    source: int = 10,
):
    return HistoricalOutcomePopulationCompletenessAssessment(
        status="COVERED",
        source_observation_count=source,
        observed_origin_start=NOW,
        observed_origin_end=NOW,
        requested_origin_start=NOW,
        requested_origin_end=NOW,
        covers_requested_start=True,
        covers_requested_end=True,
        internal_continuity_status="NOT_ASSESSED",
        warning="temporal boundary only",
    )


def import_quality(
    *,
    source: int = 10,
):
    return HistoricalOutcomeSourceImportQualityAssessment(
        status="COMPLETE",
        source_observation_count=source,
        unique_snapshot_count=source,
        imported_snapshot_count=source,
        non_imported_snapshot_count=0,
        missing_state_snapshot_count=0,
        status_counts=(("IMPORTED", source),),
        warning=None,
    )


def test_full_summary_keeps_all_component_semantics() -> None:
    summary = HistoricalOutcomeResearchProvenanceSummaryService().build(
        population_frame=frame(),
        selection_accounting=accounting(),
        population_completeness=completeness(),
        source_import_quality=import_quality(),
    )

    assert summary.complete_component_set is True
    assert summary.available_components == (
        "SOURCE_IMPORT_QUALITY",
        "POPULATION_COMPLETENESS",
        "POPULATION_FRAME",
        "SELECTION_ACCOUNTING",
    )
    assert summary.missing_components == ()


def test_partial_summary_does_not_invent_missing_components() -> None:
    summary = HistoricalOutcomeResearchProvenanceSummaryService().build(
        population_frame=frame(),
    )

    assert summary.complete_component_set is False
    assert summary.available_components == (
        "POPULATION_FRAME",
    )
    assert summary.missing_components == (
        "SOURCE_IMPORT_QUALITY",
        "POPULATION_COMPLETENESS",
        "SELECTION_ACCOUNTING",
    )


def test_serialization_uses_one_stable_provenance_envelope() -> None:
    summary = HistoricalOutcomeResearchProvenanceSummaryService().build(
        population_frame=frame(
            source=5,
            selected=2,
        ),
        selection_accounting=accounting(
            source=5,
            selected=2,
        ),
        population_completeness=completeness(
            source=5,
        ),
        source_import_quality=import_quality(
            source=5,
        ),
    )

    data = summary.to_dict()

    assert data["population_frame"]["source_observation_count"] == 5
    assert data["population_frame"]["selected_candidate_count"] == 2
    assert data["selection_accounting"]["excluded_observation_count"] == 3
    assert data["population_completeness"]["status"] == "COVERED"
    assert data["source_import_quality"]["status"] == "COMPLETE"
    assert data["complete_component_set"] is True


def test_source_denominators_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="selection_accounting source_observation_count",
    ):
        HistoricalOutcomeResearchProvenanceSummaryService().build(
            population_frame=frame(
                source=10,
                selected=4,
            ),
            selection_accounting=accounting(
                source=9,
                selected=4,
            ),
        )


def test_selected_denominator_must_match_population_frame() -> None:
    with pytest.raises(
        ValueError,
        match="selected_candidate_count",
    ):
        HistoricalOutcomeResearchProvenanceSummaryService().build(
            population_frame=frame(
                source=10,
                selected=4,
            ),
            selection_accounting=accounting(
                source=10,
                selected=3,
            ),
        )


def test_import_quality_source_denominator_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="source_import_quality source_observation_count",
    ):
        HistoricalOutcomeResearchProvenanceSummaryService().build(
            population_frame=frame(
                source=10,
                selected=4,
            ),
            source_import_quality=import_quality(
                source=9,
            ),
        )


def test_completeness_source_denominator_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="population_completeness source_observation_count",
    ):
        HistoricalOutcomeResearchProvenanceSummaryService().build(
            population_frame=frame(
                source=10,
                selected=4,
            ),
            population_completeness=completeness(
                source=9,
            ),
        )
