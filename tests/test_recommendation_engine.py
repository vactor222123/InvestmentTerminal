"""
Tests for RecommendationEngine.
"""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.ranking_models import (
    RankingCandidate,
    RankingResult,
)
from investment_terminal.portfolio.recommendation_engine import (
    RecommendationEngine,
)
from tests.test_ranking_models import (
    create_decision,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    14,
    0,
    tzinfo=timezone.utc,
)


def create_custom_candidate(
    *,
    rank: int = 1,
    symbol: str = "MSFT",
    overall: float = 80.0,
    confidence: float = 95.0,
    risk_level: str = "LOW",
    valuation: str = "FAIR",
    technical_condition: str = "STRONG",
) -> RankingCandidate:
    decision = create_decision(
        symbol
    )

    scores = replace(
        decision.scores,
        overall=overall,
    )

    confidence_result = replace(
        decision.confidence,
        score=confidence,
    )

    quality = replace(
        decision.quality,
        risk_level=risk_level,
        valuation=valuation,
        technical_condition=technical_condition,
    )

    updated_decision = replace(
        decision,
        scores=scores,
        confidence=confidence_result,
        quality=quality,
    )

    return RankingCandidate(
        rank=rank,
        decision=updated_decision,
    )


def create_ranking(
    *candidates: RankingCandidate,
) -> RankingResult:
    return RankingResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        candidates=tuple(candidates),
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (90.0, "STRONG_BUY"),
        (80.0, "BUY"),
        (70.0, "ACCUMULATE"),
        (55.0, "HOLD"),
        (40.0, "WATCH"),
        (20.0, "AVOID"),
    ],
)
def test_recommend_uses_overall_score(
    score,
    expected,
) -> None:
    ranking = create_ranking(
        create_custom_candidate(
            overall=score,
        )
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert (
        result.top_recommendation.recommendation
        == expected
    )


def test_recommend_downgrades_high_risk() -> None:
    ranking = create_ranking(
        create_custom_candidate(
            overall=90.0,
            risk_level="HIGH",
        )
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert (
        result.top_recommendation.recommendation
        == "ACCUMULATE"
    )


def test_recommend_downgrades_expensive_valuation() -> None:
    ranking = create_ranking(
        create_custom_candidate(
            overall=80.0,
            valuation="EXPENSIVE",
        )
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert (
        result.top_recommendation.recommendation
        == "ACCUMULATE"
    )


def test_recommend_downgrades_extended_technical_state() -> None:
    ranking = create_ranking(
        create_custom_candidate(
            overall=80.0,
            technical_condition=(
                "POSITIVE BUT EXTENDED"
            ),
        )
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert (
        result.top_recommendation.recommendation
        == "ACCUMULATE"
    )


def test_recommend_caps_low_confidence_at_watch() -> None:
    ranking = create_ranking(
        create_custom_candidate(
            overall=90.0,
            confidence=70.0,
        )
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert (
        result.top_recommendation.recommendation
        == "WATCH"
    )


def test_recommend_avoids_very_low_confidence() -> None:
    ranking = create_ranking(
        create_custom_candidate(
            overall=90.0,
            confidence=55.0,
        )
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert (
        result.top_recommendation.recommendation
        == "AVOID"
    )


def test_recommend_preserves_ranking_order() -> None:
    ranking = create_ranking(
        create_custom_candidate(
            rank=1,
            symbol="GOOGL",
            overall=88.0,
        ),
        create_custom_candidate(
            rank=2,
            symbol="MSFT",
            overall=80.0,
        ),
        create_custom_candidate(
            rank=3,
            symbol="AAPL",
            overall=70.0,
        ),
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert [
        recommendation.symbol
        for recommendation
        in result.recommendations
    ] == [
        "GOOGL",
        "MSFT",
        "AAPL",
    ]

    assert [
        recommendation.rank
        for recommendation
        in result.recommendations
    ] == [
        1,
        2,
        3,
    ]


def test_recommend_builds_explanations() -> None:
    ranking = create_ranking(
        create_custom_candidate(
            symbol="GOOGL",
            overall=88.0,
            risk_level="MEDIUM",
            valuation="ELEVATED",
            technical_condition=(
                "POSITIVE BUT EXTENDED"
            ),
        )
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    recommendation = (
        result.top_recommendation
    )

    assert recommendation.rationale
    assert recommendation.cautions

    assert any(
        "highest-ranked" in item
        for item in recommendation.rationale
    )

    assert (
        "The current risk level is medium."
        in recommendation.cautions
    )
    assert (
        "Valuation is elevated."
        in recommendation.cautions
    )


def test_recommend_uses_generated_at() -> None:
    ranking = create_ranking(
        create_custom_candidate()
    )

    result = RecommendationEngine().recommend(
        ranking,
        generated_at=GENERATED_AT,
    )

    assert result.generated_at == GENERATED_AT
    assert result.schema_version == "1.0"


def test_recommend_rejects_invalid_ranking() -> None:
    with pytest.raises(
        TypeError,
        match="RankingResult",
    ):
        RecommendationEngine().recommend(
            None
        )


def test_recommend_rejects_invalid_generated_at() -> None:
    ranking = create_ranking(
        create_custom_candidate()
    )

    with pytest.raises(
        TypeError,
        match="generated_at",
    ):
        RecommendationEngine().recommend(
            ranking,
            generated_at="2026-08-01",
        )