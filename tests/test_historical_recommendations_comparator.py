"""
Tests for HistoricalRecommendationsComparator.
"""

import pytest

from investment_terminal.history.historical_recommendation_models import (
    HistoricalRecommendation,
)
from investment_terminal.history.historical_recommendations_comparator import (
    HistoricalRecommendationsComparator,
)


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)


def recommendation(
    snapshot_id: str,
    key: str,
    *,
    symbol: str = "BABA",
    action: str = "BUY",
    score: float | None = 80.0,
    confidence: float | None = 0.8,
    rationale: str = "Value",
    payload: dict | None = None,
) -> HistoricalRecommendation:
    return HistoricalRecommendation(
        snapshot_id=snapshot_id,
        recommendation_key=key,
        symbol=symbol,
        action=action,
        score=score,
        confidence=confidence,
        rationale=rationale,
        payload=(
            payload
            if payload is not None
            else {
                "symbol": symbol,
                "action": action,
            }
        ),
    )


def test_comparator_detects_added_removed_changed_and_unchanged() -> None:
    result = HistoricalRecommendationsComparator().compare(
        previous=(
            recommendation(
                FIRST_ID,
                "DROP",
            ),
            recommendation(
                FIRST_ID,
                "KEEP",
            ),
            recommendation(
                FIRST_ID,
                "MOVE",
            ),
        ),
        current=(
            recommendation(
                SECOND_ID,
                "KEEP",
            ),
            recommendation(
                SECOND_ID,
                "MOVE",
                score=90.0,
                confidence=0.9,
            ),
            recommendation(
                SECOND_ID,
                "NEW",
            ),
        ),
    )

    assert [
        item.recommendation_key
        for item in result
    ] == [
        "DROP",
        "KEEP",
        "MOVE",
        "NEW",
    ]

    by_key = {
        item.recommendation_key: item
        for item in result
    }

    assert by_key[
        "DROP"
    ].change_type == "REMOVED"
    assert by_key[
        "KEEP"
    ].change_type == "UNCHANGED"
    assert by_key[
        "MOVE"
    ].change_type == "CHANGED"
    assert by_key[
        "NEW"
    ].change_type == "ADDED"

    assert by_key[
        "MOVE"
    ].score.absolute_change == 10.0
    assert by_key[
        "MOVE"
    ].confidence.absolute_change == pytest.approx(
        0.1
    )


def test_action_change_marks_recommendation_changed() -> None:
    result = HistoricalRecommendationsComparator().compare(
        previous=(
            recommendation(
                FIRST_ID,
                "BABA",
                action="HOLD",
            ),
        ),
        current=(
            recommendation(
                SECOND_ID,
                "BABA",
                action="BUY",
            ),
        ),
    )

    change = result[
        0
    ]

    assert change.change_type == "CHANGED"
    assert change.previous[
        "action"
    ] == "HOLD"
    assert change.current[
        "action"
    ] == "BUY"


def test_payload_change_marks_recommendation_changed() -> None:
    result = HistoricalRecommendationsComparator().compare(
        previous=(
            recommendation(
                FIRST_ID,
                "BABA",
                payload={
                    "symbol": "BABA",
                    "action": "BUY",
                    "tag": "old",
                },
            ),
        ),
        current=(
            recommendation(
                SECOND_ID,
                "BABA",
                payload={
                    "symbol": "BABA",
                    "action": "BUY",
                    "tag": "new",
                },
            ),
        ),
    )

    assert result[
        0
    ].change_type == "CHANGED"


def test_optional_scores_keep_absent_value_semantics() -> None:
    result = HistoricalRecommendationsComparator().compare(
        previous=(
            recommendation(
                FIRST_ID,
                "BABA",
                score=None,
                confidence=None,
            ),
        ),
        current=(
            recommendation(
                SECOND_ID,
                "BABA",
                score=75.0,
                confidence=0.7,
            ),
        ),
    )

    change = result[
        0
    ]

    assert change.score.previous is None
    assert change.score.current == 75.0
    assert change.score.absolute_change is None
    assert change.confidence.percentage_change is None


def test_different_keys_are_not_implicitly_matched() -> None:
    result = HistoricalRecommendationsComparator().compare(
        previous=(
            recommendation(
                FIRST_ID,
                "OLD",
                symbol="BABA",
            ),
        ),
        current=(
            recommendation(
                SECOND_ID,
                "NEW",
                symbol="BABA",
            ),
        ),
    )

    assert [
        (
            item.recommendation_key,
            item.change_type,
        )
        for item in result
    ] == [
        (
            "NEW",
            "ADDED",
        ),
        (
            "OLD",
            "REMOVED",
        ),
    ]


def test_comparator_rejects_duplicate_keys() -> None:
    duplicate = recommendation(
        FIRST_ID,
        "BABA",
    )

    with pytest.raises(
        ValueError,
        match="duplicate recommendation_key BABA",
    ):
        HistoricalRecommendationsComparator().compare(
            previous=(
                duplicate,
                duplicate,
            ),
            current=(),
        )
