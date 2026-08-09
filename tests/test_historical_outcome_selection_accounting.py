"""
Tests for historical outcome query selection-reason accounting.
"""

from datetime import datetime, timedelta, timezone

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
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
    HistoricalOutcomeQueryService,
)
from investment_terminal.history.historical_outcome_selection_accounting import (
    HistoricalOutcomeSelectionAccountingService,
)


ORIGIN = datetime(
    2026,
    8,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


def result(
    *,
    recommendation_key: str = "WORLD",
    symbol: str = "IWDA",
    action: str = "BUY",
    status: str = "PARTIAL",
    window_value: int = 5,
    origin_at: datetime = ORIGIN,
) -> HistoricalMethodologyAwareObservationResult:
    return HistoricalMethodologyAwareObservationResult(
        methodology=HistoricalOutcomeMethodology.sprint_14_exact_close_v1(),
        observation=HistoricalRecommendationObservation(
            origin_snapshot_id="11111111-1111-4111-8111-111111111111",
            recommendation_key=recommendation_key,
            symbol=symbol,
            action=action,
            origin_at=origin_at,
            window=HistoricalObservationWindow(
                kind="ELAPSED_DAYS",
                value=window_value,
            ),
            status=status,
            evidence=None,
            warnings=(),
        ),
        outcome=None,
        origin_selected_evidence=None,
        endpoint_methodology_evidence=None,
    )


def reason_map(
    accounting: object,
) -> dict[str, int]:
    return {
        item.reason: item.count
        for item in accounting.reason_counts  # type: ignore[attr-defined]
    }


def test_no_filters_have_no_exclusions_or_reasons() -> None:
    accounting = HistoricalOutcomeSelectionAccountingService().assess(
        (
            result(),
            result(
                symbol="EIMI",
            ),
        ),
        query=HistoricalOutcomeQuery(),
    )

    assert accounting.source_observation_count == 2
    assert accounting.selected_candidate_count == 2
    assert accounting.excluded_observation_count == 0
    assert accounting.reason_counts == ()
    assert accounting.total_reason_failures == 0


def test_single_filter_reason_is_counted() -> None:
    source = (
        result(
            symbol="IWDA",
        ),
        result(
            symbol="EIMI",
        ),
    )
    query = HistoricalOutcomeQuery(
        symbol="IWDA",
    )

    accounting = HistoricalOutcomeSelectionAccountingService().assess(
        source,
        query=query,
    )

    assert accounting.selected_candidate_count == 1
    assert accounting.excluded_observation_count == 1
    assert reason_map(
        accounting
    ) == {
        "SYMBOL": 1,
    }

    assert HistoricalOutcomeQueryService().filter(
        source,
        query=query,
    ) == (
        source[
            0
        ],
    )


def test_one_observation_can_fail_multiple_selection_reasons() -> None:
    source = (
        result(
            symbol="EIMI",
            action="HOLD",
            window_value=10,
        ),
    )
    query = HistoricalOutcomeQuery(
        symbol="IWDA",
        action="BUY",
        window_value=5,
    )

    accounting = HistoricalOutcomeSelectionAccountingService().assess(
        source,
        query=query,
    )

    assert accounting.excluded_observation_count == 1
    assert reason_map(
        accounting
    ) == {
        "SYMBOL": 1,
        "ACTION": 1,
        "WINDOW_VALUE": 1,
    }
    assert accounting.total_reason_failures == 3


def test_origin_range_reasons_are_distinct() -> None:
    source = (
        result(
            origin_at=ORIGIN - timedelta(days=10),
        ),
        result(
            origin_at=ORIGIN,
        ),
        result(
            origin_at=ORIGIN + timedelta(days=10),
        ),
    )
    query = HistoricalOutcomeQuery(
        origin_from=ORIGIN - timedelta(days=1),
        origin_to=ORIGIN + timedelta(days=1),
    )

    accounting = HistoricalOutcomeSelectionAccountingService().assess(
        source,
        query=query,
    )

    assert accounting.selected_candidate_count == 1
    assert reason_map(
        accounting
    ) == {
        "ORIGIN_FROM": 1,
        "ORIGIN_TO": 1,
    }


def test_serialization_states_that_reason_counts_are_not_exclusive() -> None:
    accounting = HistoricalOutcomeSelectionAccountingService().assess(
        (
            result(
                symbol="EIMI",
                action="HOLD",
            ),
        ),
        query=HistoricalOutcomeQuery(
            symbol="IWDA",
            action="BUY",
        ),
    )

    data = accounting.to_dict()

    assert data["source_observation_count"] == 1
    assert data["selected_candidate_count"] == 0
    assert data["excluded_observation_count"] == 1
    assert data["total_reason_failures"] == 2
    assert data["reason_counts_are_exclusive"] is False


def test_reason_order_is_deterministic() -> None:
    accounting = HistoricalOutcomeSelectionAccountingService().assess(
        (
            result(
                recommendation_key="EMERGING",
                symbol="EIMI",
                action="HOLD",
                window_value=10,
            ),
        ),
        query=HistoricalOutcomeQuery(
            recommendation_key="WORLD",
            symbol="IWDA",
            action="BUY",
            window_value=5,
        ),
    )

    assert tuple(
        item.reason
        for item in accounting.reason_counts
    ) == (
        "RECOMMENDATION_KEY",
        "SYMBOL",
        "ACTION",
        "WINDOW_VALUE",
    )
