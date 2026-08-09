"""
Tests for research population metadata and selection-bias guardrails.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
)
from investment_terminal.history.historical_outcome_research_population import (
    HistoricalOutcomeResearchPopulationMetadataService,
)


START = datetime(
    2026,
    1,
    1,
    tzinfo=timezone.utc,
)
END = datetime(
    2026,
    6,
    30,
    tzinfo=timezone.utc,
)


def test_unfiltered_population_is_explicit_and_warned() -> None:
    metadata = HistoricalOutcomeResearchPopulationMetadataService().build(
        query=HistoricalOutcomeQuery(),
        candidate_count=25,
    )

    assert metadata.selection_basis == "ARCHIVED_OBSERVATIONS"
    assert metadata.candidate_count == 25
    assert metadata.prefiltered is False
    assert len(metadata.warnings) == 1
    assert "not automatically an unbiased" in metadata.warnings[0]


def test_filtered_population_preserves_requested_selection() -> None:
    metadata = HistoricalOutcomeResearchPopulationMetadataService().build(
        query=HistoricalOutcomeQuery(
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            window_kind="ELAPSED_DAYS",
            window_value=5,
            methodology_id="ELAPSED_DAYS_EXACT_CLOSE",
            methodology_version=1,
            origin_from=START,
            origin_to=END,
        ),
        candidate_count=8,
    )

    assert metadata.prefiltered is True
    assert metadata.requested_recommendation_key == "WORLD"
    assert metadata.requested_symbol == "IWDA"
    assert metadata.requested_action == "BUY"
    assert metadata.requested_window_value == 5
    assert metadata.origin_start == START
    assert metadata.origin_end == END
    assert len(metadata.warnings) == 2
    assert "prefiltered" in metadata.warnings[1]


def test_serialization_preserves_population_denominator_and_filters() -> None:
    metadata = HistoricalOutcomeResearchPopulationMetadataService().build(
        query=HistoricalOutcomeQuery(
            action="HOLD",
        ),
        candidate_count=3,
    )

    data = metadata.to_dict()

    assert data["selection_basis"] == "ARCHIVED_OBSERVATIONS"
    assert data["candidate_count"] == 3
    assert data["requested_action"] == "HOLD"
    assert data["prefiltered"] is True
    assert isinstance(data["warnings"], list)


def test_candidate_count_is_validated() -> None:
    with pytest.raises(
        ValueError,
        match="candidate_count",
    ):
        HistoricalOutcomeResearchPopulationMetadataService().build(
            query=HistoricalOutcomeQuery(),
            candidate_count=-1,
        )


def test_service_rejects_invalid_query() -> None:
    with pytest.raises(
        TypeError,
        match="query",
    ):
        HistoricalOutcomeResearchPopulationMetadataService().build(
            query=object(),  # type: ignore[arg-type]
            candidate_count=0,
        )
