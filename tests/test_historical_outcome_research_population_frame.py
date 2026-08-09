"""
Tests for the explicit historical research population frame.
"""

import pytest

from investment_terminal.history.historical_outcome_research_population_frame import (
    HistoricalOutcomeResearchPopulationFrame,
    HistoricalOutcomeResearchPopulationFrameService,
)


def test_unfiltered_frame_preserves_full_denominator() -> None:
    frame = HistoricalOutcomeResearchPopulationFrameService().build(
        source_observation_count=12,
        selected_candidate_count=12,
    )

    assert frame.frame_basis == (
        "ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS"
    )
    assert frame.source_observation_count == 12
    assert frame.selected_candidate_count == 12
    assert frame.excluded_by_selection_count == 0
    assert frame.selection_fraction == 1.0
    assert frame.selection_applied is False


def test_filtered_frame_makes_selection_loss_explicit() -> None:
    frame = HistoricalOutcomeResearchPopulationFrameService().build(
        source_observation_count=120,
        selected_candidate_count=8,
    )

    assert frame.excluded_by_selection_count == 112
    assert frame.selection_fraction == pytest.approx(
        8 / 120
    )
    assert frame.selection_applied is True


def test_zero_source_population_is_explicit() -> None:
    frame = HistoricalOutcomeResearchPopulationFrameService().build(
        source_observation_count=0,
        selected_candidate_count=0,
    )

    assert frame.selection_fraction == 0.0
    assert frame.selection_applied is False


def test_serialization_preserves_both_denominators() -> None:
    frame = HistoricalOutcomeResearchPopulationFrameService().build(
        source_observation_count=10,
        selected_candidate_count=4,
    )

    assert frame.to_dict() == {
        "frame_basis": "ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS",
        "source_observation_count": 10,
        "selected_candidate_count": 4,
        "excluded_by_selection_count": 6,
        "selection_fraction": 0.4,
        "selection_applied": True,
    }


def test_selected_count_cannot_exceed_source_count() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed",
    ):
        HistoricalOutcomeResearchPopulationFrameService().build(
            source_observation_count=3,
            selected_candidate_count=4,
        )


def test_model_rejects_inconsistent_excluded_count() -> None:
    with pytest.raises(
        ValueError,
        match="excluded_by_selection_count",
    ):
        HistoricalOutcomeResearchPopulationFrame(
            frame_basis="ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS",
            source_observation_count=10,
            selected_candidate_count=4,
            excluded_by_selection_count=5,
            selection_fraction=0.4,
        )


def test_model_rejects_inconsistent_selection_fraction() -> None:
    with pytest.raises(
        ValueError,
        match="selection_fraction",
    ):
        HistoricalOutcomeResearchPopulationFrame(
            frame_basis="ARCHIVED_METHODOLOGY_AWARE_OBSERVATIONS",
            source_observation_count=10,
            selected_candidate_count=4,
            excluded_by_selection_count=6,
            selection_fraction=0.5,
        )


@pytest.mark.parametrize(
    ("source", "selected"),
    [
        (-1, 0),
        (1, -1),
        (True, 0),
        (1, False),
    ],
)
def test_service_rejects_invalid_counts(
    source: object,
    selected: object,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        HistoricalOutcomeResearchPopulationFrameService().build(
            source_observation_count=source,  # type: ignore[arg-type]
            selected_candidate_count=selected,  # type: ignore[arg-type]
        )
