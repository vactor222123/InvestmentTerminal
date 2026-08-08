"""
Focused regression tests for recommendation transition model semantics.
"""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
    HistoricalRecommendationTransition,
)


FIRST_ID = "11111111-1111-4111-8111-111111111111"
SECOND_ID = "22222222-2222-4222-8222-222222222222"
T0 = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=1)


def state(
    snapshot_id: str,
    generated_at: datetime,
    *,
    symbol: str = "IWDA",
    action: str = "BUY",
    score: float = 80.0,
) -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id=snapshot_id,
        generated_at=generated_at,
        recommendation_key="WORLD",
        present=True,
        symbol=symbol,
        action=action,
        score=score,
        confidence=0.8,
    )


def test_descriptive_changed_represents_symbol_only_change() -> None:
    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type="DESCRIPTIVE_CHANGED",
        previous=state(
            FIRST_ID,
            T0,
            symbol="IWDA",
        ),
        current=state(
            SECOND_ID,
            T1,
            symbol="SWDA",
        ),
        duration_seconds=86400.0,
    )

    assert transition.transition_type == "DESCRIPTIVE_CHANGED"


def test_descriptive_changed_rejects_metric_change() -> None:
    with pytest.raises(
        ValueError,
        match="DESCRIPTIVE_CHANGED requires",
    ):
        HistoricalRecommendationTransition(
            recommendation_key="WORLD",
            transition_type="DESCRIPTIVE_CHANGED",
            previous=state(
                FIRST_ID,
                T0,
                score=80.0,
            ),
            current=state(
                SECOND_ID,
                T1,
                symbol="SWDA",
                score=81.0,
            ),
            duration_seconds=86400.0,
        )
