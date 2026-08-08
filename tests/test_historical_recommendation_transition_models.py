"""
Tests for historical recommendation transition models.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
    HistoricalRecommendationTransition,
)


FIRST_ID = "11111111-1111-4111-8111-111111111111"
SECOND_ID = "22222222-2222-4222-8222-222222222222"
THIRD_ID = "33333333-3333-4333-8333-333333333333"

T0 = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)
T1 = T0 + timedelta(days=1)


def present_state(
    snapshot_id: str,
    generated_at: datetime,
    *,
    action: str = "BUY",
    score: float | None = 80.0,
    confidence: float | None = 0.8,
) -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id=snapshot_id,
        generated_at=generated_at,
        recommendation_key="WORLD",
        present=True,
        symbol="iwda",
        action=action,
        score=score,
        confidence=confidence,
    )


def absent_state(
    snapshot_id: str,
    generated_at: datetime,
) -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id=snapshot_id,
        generated_at=generated_at,
        recommendation_key="WORLD",
        present=False,
    )


def test_state_normalizes_identity_and_values() -> None:
    state = present_state(
        FIRST_ID,
        T0,
        action=" buy ",
    )

    assert state.recommendation_key == "WORLD"
    assert state.symbol == "IWDA"
    assert state.action == "BUY"
    assert state.score == 80.0
    assert state.confidence == 0.8


def test_absent_state_rejects_recommendation_values() -> None:
    with pytest.raises(
        ValueError,
        match="absent recommendation state",
    ):
        HistoricalRecommendationState(
            snapshot_id=FIRST_ID,
            generated_at=T0,
            recommendation_key="WORLD",
            present=False,
            action="BUY",
        )


def test_first_observed_has_no_duration() -> None:
    current = present_state(
        FIRST_ID,
        T0,
    )

    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type=" first_observed ",
        previous=None,
        current=current,
        duration_seconds=None,
    )

    assert transition.transition_type == "FIRST_OBSERVED"
    assert transition.duration_seconds is None


def test_action_changed_transition() -> None:
    previous = present_state(
        FIRST_ID,
        T0,
        action="BUY",
    )
    current = present_state(
        SECOND_ID,
        T1,
        action="HOLD",
    )

    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type="ACTION_CHANGED",
        previous=previous,
        current=current,
        duration_seconds=86400.0,
    )

    assert transition.transition_type == "ACTION_CHANGED"
    assert transition.duration_seconds == 86400.0


def test_metrics_changed_requires_same_action() -> None:
    previous = present_state(
        FIRST_ID,
        T0,
        score=80.0,
        confidence=0.8,
    )
    current = present_state(
        SECOND_ID,
        T1,
        score=75.0,
        confidence=0.7,
    )

    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type="METRICS_CHANGED",
        previous=previous,
        current=current,
        duration_seconds=86400.0,
    )

    assert transition.transition_type == "METRICS_CHANGED"


def test_disappeared_transition() -> None:
    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type="DISAPPEARED",
        previous=present_state(
            FIRST_ID,
            T0,
        ),
        current=absent_state(
            SECOND_ID,
            T1,
        ),
        duration_seconds=86400.0,
    )

    assert transition.current.present is False


def test_reappeared_transition() -> None:
    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type="REAPPEARED",
        previous=absent_state(
            FIRST_ID,
            T0,
        ),
        current=present_state(
            SECOND_ID,
            T1,
        ),
        duration_seconds=86400.0,
    )

    assert transition.current.present is True


def test_unchanged_requires_equivalent_state() -> None:
    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type="UNCHANGED",
        previous=present_state(
            FIRST_ID,
            T0,
        ),
        current=present_state(
            SECOND_ID,
            T1,
        ),
        duration_seconds=86400.0,
    )

    assert transition.transition_type == "UNCHANGED"


def test_unchanged_rejects_metric_difference() -> None:
    with pytest.raises(
        ValueError,
        match="UNCHANGED requires equivalent",
    ):
        HistoricalRecommendationTransition(
            recommendation_key="WORLD",
            transition_type="UNCHANGED",
            previous=present_state(
                FIRST_ID,
                T0,
                score=80.0,
            ),
            current=present_state(
                SECOND_ID,
                T1,
                score=81.0,
            ),
            duration_seconds=86400.0,
        )


def test_transition_requires_chronological_states() -> None:
    with pytest.raises(
        ValueError,
        match="must be later",
    ):
        HistoricalRecommendationTransition(
            recommendation_key="WORLD",
            transition_type="UNCHANGED",
            previous=present_state(
                FIRST_ID,
                T1,
            ),
            current=present_state(
                SECOND_ID,
                T0,
            ),
            duration_seconds=0.0,
        )


def test_transition_requires_exact_duration() -> None:
    with pytest.raises(
        ValueError,
        match="must match the state timestamps",
    ):
        HistoricalRecommendationTransition(
            recommendation_key="WORLD",
            transition_type="UNCHANGED",
            previous=present_state(
                FIRST_ID,
                T0,
            ),
            current=present_state(
                SECOND_ID,
                T1,
            ),
            duration_seconds=123.0,
        )


def test_transition_rejects_key_mismatch() -> None:
    current = HistoricalRecommendationState(
        snapshot_id=SECOND_ID,
        generated_at=T1,
        recommendation_key="EM",
        present=True,
        symbol="EIMI",
        action="BUY",
        score=70.0,
        confidence=0.7,
    )

    with pytest.raises(
        ValueError,
        match="current recommendation_key must match",
    ):
        HistoricalRecommendationTransition(
            recommendation_key="WORLD",
            transition_type="FIRST_OBSERVED",
            previous=None,
            current=current,
            duration_seconds=None,
        )


def test_models_are_frozen() -> None:
    state = present_state(
        FIRST_ID,
        T0,
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        state.action = "SELL"  # type: ignore[misc]


def test_transition_to_dict_is_json_ready() -> None:
    transition = HistoricalRecommendationTransition(
        recommendation_key="WORLD",
        transition_type="ACTION_CHANGED",
        previous=present_state(
            FIRST_ID,
            T0,
            action="BUY",
        ),
        current=present_state(
            SECOND_ID,
            T1,
            action="HOLD",
        ),
        duration_seconds=86400.0,
    )

    data = transition.to_dict()

    assert data["recommendation_key"] == "WORLD"
    assert data["transition_type"] == "ACTION_CHANGED"
    assert data["previous"]["action"] == "BUY"
    assert data["current"]["action"] == "HOLD"
    assert data["duration_seconds"] == 86400.0
