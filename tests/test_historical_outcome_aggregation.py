"""
Tests for pure historical outcome aggregation.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindow,
)
from investment_terminal.history.historical_outcome_aggregation import (
    HistoricalOutcomeAggregator,
    HistoricalOutcomeSummary,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_observation_service import (
    HistoricalOutcomeObservationResult,
)


SNAPSHOT_IDS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    "33333333-3333-4333-8333-333333333333",
    "44444444-4444-4444-8444-444444444444",
)
ORIGIN = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def result(
    index: int,
    *,
    status: str,
    action: str | None,
    movement: float | None = None,
) -> HistoricalOutcomeObservationResult:
    observation = HistoricalRecommendationObservation(
        origin_snapshot_id=SNAPSHOT_IDS[index],
        recommendation_key=f"REC-{index}",
        symbol="IWDA",
        action=action,
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=5,
        ),
        status=status,
        evidence=None,
        warnings=(),
    )

    outcome = None
    if movement is not None:
        endpoint_price = 100.0 * (
            1.0
            + movement
        )
        outcome = HistoricalRecommendationOutcome(
            instrument_key="IWDA",
            currency="EUR",
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            price_change=price_change,
            price_change_fraction=price_change_fraction,
            origin_source="history",
            endpoint_source="history",
        )

    return HistoricalOutcomeObservationResult(
        observation=observation,
        outcome=outcome,
    )


def complete_result(
    index: int,
    *,
    action: str,
    movement: float,
) -> HistoricalOutcomeObservationResult:
    origin_price = 100.0
    endpoint_price = origin_price * (
        1.0
        + movement
    )
    price_change = (
        endpoint_price
        - origin_price
    )
    price_change_fraction = (
        endpoint_price
        / origin_price
    ) - 1.0
    observation = HistoricalRecommendationObservation(
        origin_snapshot_id=SNAPSHOT_IDS[index],
        recommendation_key=f"REC-{index}",
        symbol="IWDA",
        action=action,
        origin_at=ORIGIN,
        window=HistoricalObservationWindow(
            kind="ELAPSED_DAYS",
            value=5,
        ),
        status="COMPLETE",
        evidence=HistoricalOutcomeEvidence(
            instrument_key="IWDA",
            origin_at=ORIGIN,
            endpoint_at=ORIGIN,
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            origin_source="history",
            endpoint_source="history",
            origin_currency="EUR",
            endpoint_currency="EUR",
            origin_resolution="D",
            endpoint_resolution="D",
        ),
        warnings=(),
    )
    return HistoricalOutcomeObservationResult(
        observation=observation,
        outcome=HistoricalRecommendationOutcome(
            instrument_key="IWDA",
            currency="EUR",
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            price_change=price_change,
            price_change_fraction=price_change_fraction,
            origin_source="history",
            endpoint_source="history",
        ),
    )


def test_summarizes_status_counts_and_complete_coverage() -> None:
    summary = HistoricalOutcomeAggregator().summarize(
        (
            complete_result(
                0,
                action="BUY",
                movement=0.10,
            ),
            complete_result(
                1,
                action="HOLD",
                movement=-0.05,
            ),
            result(
                2,
                status="PARTIAL",
                action="BUY",
            ),
            result(
                3,
                status="NOT_MATURE",
                action="HOLD",
            ),
        )
    )

    assert summary.total_count == 4
    assert summary.complete_count == 2
    assert summary.partial_count == 1
    assert summary.unavailable_count == 0
    assert summary.not_mature_count == 1
    assert summary.coverage_fraction == 0.5


def test_summarizes_raw_price_movement_only_for_complete_observations() -> None:
    summary = HistoricalOutcomeAggregator().summarize(
        (
            complete_result(
                0,
                action="BUY",
                movement=0.10,
            ),
            complete_result(
                1,
                action="BUY",
                movement=-0.05,
            ),
            complete_result(
                2,
                action="HOLD",
                movement=0.20,
            ),
        )
    )

    assert summary.mean_price_change_fraction == pytest.approx(
        (0.10 - 0.05 + 0.20)
        / 3
    )
    assert summary.median_price_change_fraction == pytest.approx(
        0.10
    )


def test_action_counts_are_deterministically_sorted() -> None:
    summary = HistoricalOutcomeAggregator().summarize(
        (
            complete_result(
                0,
                action="HOLD",
                movement=0.01,
            ),
            complete_result(
                1,
                action="BUY",
                movement=0.02,
            ),
            result(
                2,
                status="PARTIAL",
                action="BUY",
            ),
        )
    )

    assert [
        item.to_dict()
        for item in summary.action_counts
    ] == [
        {
            "action": "BUY",
            "count": 2,
        },
        {
            "action": "HOLD",
            "count": 1,
        },
    ]


def test_empty_input_has_no_invented_statistics() -> None:
    summary = HistoricalOutcomeAggregator().summarize(
        ()
    )

    assert summary.total_count == 0
    assert summary.coverage_fraction is None
    assert summary.mean_price_change_fraction is None
    assert summary.median_price_change_fraction is None
    assert summary.action_counts == ()


def test_non_complete_only_input_has_no_price_summary() -> None:
    summary = HistoricalOutcomeAggregator().summarize(
        (
            result(
                0,
                status="UNAVAILABLE",
                action=None,
            ),
            result(
                1,
                status="NOT_MATURE",
                action="BUY",
            ),
        )
    )

    assert summary.complete_count == 0
    assert summary.mean_price_change_fraction is None
    assert summary.median_price_change_fraction is None


def test_output_avoids_effectiveness_and_performance_claims() -> None:
    summary = HistoricalOutcomeAggregator().summarize(
        (
            complete_result(
                0,
                action="BUY",
                movement=0.10,
            ),
        )
    )

    data = summary.to_dict()

    assert "success_rate" not in data
    assert "hit_rate" not in data
    assert "confidence" not in data
    assert "effectiveness" not in data
    assert "performance" not in {
        key
        for key in data
    }
    assert "not portfolio performance" in data[
        "metric_semantics"
    ]


def test_summary_rejects_inconsistent_status_counts() -> None:
    with pytest.raises(
        ValueError,
        match="status counts must sum",
    ):
        HistoricalOutcomeSummary(
            total_count=2,
            complete_count=1,
            partial_count=0,
            unavailable_count=0,
            not_mature_count=0,
            coverage_fraction=0.5,
            mean_price_change_fraction=0.1,
            median_price_change_fraction=0.1,
            action_counts=(),
        )
