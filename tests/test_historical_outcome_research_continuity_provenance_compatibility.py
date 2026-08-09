"""
Compatibility contract for optional archive-gap provenance.
"""

from datetime import datetime, timezone

from investment_terminal.history.historical_archive_gap_assessment import (
    HistoricalArchiveGapAssessmentService,
)
from investment_terminal.history.historical_outcome_research_provenance import (
    HistoricalOutcomeResearchProvenanceSummaryService,
)
from investment_terminal.history.historical_outcome_research_population_frame import (
    HistoricalOutcomeResearchPopulationFrame,
)


def dt(day: int) -> datetime:
    return datetime(2026, 8, day, 12, 0, tzinfo=timezone.utc)


def frame() -> HistoricalOutcomeResearchPopulationFrame:
    return HistoricalOutcomeResearchPopulationFrame(
        frame_basis="ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS",
        source_observation_count=1,
        selected_candidate_count=1,
        excluded_by_selection_count=0,
        selection_fraction=1.0,
    )


def test_archive_gap_is_optional_extension_not_core_missing_component() -> None:
    summary = HistoricalOutcomeResearchProvenanceSummaryService().build(
        population_frame=frame(),
    )

    assert summary.available_components == ("POPULATION_FRAME",)
    assert summary.missing_components == (
        "SOURCE_IMPORT_QUALITY",
        "POPULATION_COMPLETENESS",
        "SELECTION_ACCOUNTING",
    )
    assert summary.available_optional_components == ()


def test_archive_gap_is_serialized_without_changing_core_component_semantics() -> None:
    gaps = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(dt(1), dt(2), dt(3)),
        observed_timestamps=(dt(1), dt(3)),
    )

    summary = HistoricalOutcomeResearchProvenanceSummaryService().build(
        population_frame=frame(),
        archive_gap_assessment=gaps,
    )
    data = summary.to_dict()

    assert summary.available_components == ("POPULATION_FRAME",)
    assert summary.available_optional_components == (
        "ARCHIVE_GAP_ASSESSMENT",
    )
    assert data["archive_gap_assessment"]["status"] == "GAPS"
    assert data["available_optional_components"] == [
        "ARCHIVE_GAP_ASSESSMENT"
    ]


def test_optional_gap_does_not_change_core_complete_component_set() -> None:
    # With only population frame, core set remains incomplete regardless of
    # whether the optional archive-gap extension is present.
    gaps = HistoricalArchiveGapAssessmentService().assess(
        expected_timestamps=(dt(1),),
        observed_timestamps=(dt(1),),
    )

    without_gap = HistoricalOutcomeResearchProvenanceSummaryService().build(
        population_frame=frame(),
    )
    with_gap = HistoricalOutcomeResearchProvenanceSummaryService().build(
        population_frame=frame(),
        archive_gap_assessment=gaps,
    )

    assert without_gap.complete_component_set is False
    assert with_gap.complete_component_set is False
    assert without_gap.missing_components == with_gap.missing_components
