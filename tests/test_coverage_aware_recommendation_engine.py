"""
Tests for coverage-aware recommendation safety controls.
"""

from dataclasses import replace
from datetime import datetime, timezone

from investment_terminal.market.analysis_coverage_policy import (
    SPECIALIZED_BANK_WARNING,
)
from investment_terminal.portfolio.coverage_aware_recommendation_engine import (
    CoverageAwareRecommendationEngine,
)
from investment_terminal.portfolio.ranking_models import (
    RankingCandidate,
    RankingResult,
)
from tests.test_ranking_models import (
    create_decision,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    18,
    0,
    tzinfo=timezone.utc,
)


def create_candidate(
    *,
    symbol: str,
    rank: int,
    overall: float,
    risk_factors: tuple[str, ...] = (),
) -> RankingCandidate:
    decision = create_decision(
        symbol
    )
    decision = replace(
        decision,
        scores=replace(
            decision.scores,
            overall=overall,
        ),
        confidence=replace(
            decision.confidence,
            score=95.0,
        ),
        quality=replace(
            decision.quality,
            risk_level="LOW",
            valuation="FAIR",
            technical_condition="STRONG",
        ),
        risk_factors=risk_factors,
    )

    return RankingCandidate(
        rank=rank,
        decision=decision,
    )


def create_ranking(
    *candidates: RankingCandidate,
) -> RankingResult:
    return RankingResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        candidates=tuple(candidates),
    )


def test_full_coverage_preserves_buy() -> None:
    ranking = create_ranking(
        create_candidate(
            symbol="GOOGL",
            rank=1,
            overall=82.0,
        )
    )

    result = (
        CoverageAwareRecommendationEngine()
        .recommend(
            ranking,
            generated_at=GENERATED_AT,
        )
    )

    assert (
        result.top_recommendation.recommendation
        == "BUY"
    )


def test_reduced_bank_coverage_caps_buy_at_watch() -> None:
    ranking = create_ranking(
        create_candidate(
            symbol="JPM",
            rank=1,
            overall=82.0,
            risk_factors=(
                SPECIALIZED_BANK_WARNING,
            ),
        )
    )

    result = (
        CoverageAwareRecommendationEngine()
        .recommend(
            ranking,
            generated_at=GENERATED_AT,
        )
    )

    recommendation = result.top_recommendation

    assert recommendation.recommendation == "WATCH"
    assert (
        CoverageAwareRecommendationEngine
        .COVERAGE_CAUTION
        in recommendation.cautions
    )


def test_coverage_cap_never_strengthens_label() -> None:
    ranking = create_ranking(
        create_candidate(
            symbol="JPM",
            rank=1,
            overall=20.0,
            risk_factors=(
                SPECIALIZED_BANK_WARNING,
            ),
        )
    )

    result = (
        CoverageAwareRecommendationEngine()
        .recommend(
            ranking,
            generated_at=GENERATED_AT,
        )
    )

    assert (
        result.top_recommendation.recommendation
        == "AVOID"
    )


def test_ranking_order_is_preserved() -> None:
    ranking = create_ranking(
        create_candidate(
            symbol="GOOGL",
            rank=1,
            overall=82.0,
        ),
        create_candidate(
            symbol="JPM",
            rank=2,
            overall=80.0,
            risk_factors=(
                SPECIALIZED_BANK_WARNING,
            ),
        ),
    )

    result = (
        CoverageAwareRecommendationEngine()
        .recommend(
            ranking,
            generated_at=GENERATED_AT,
        )
    )

    assert [
        item.symbol
        for item in result.recommendations
    ] == [
        "GOOGL",
        "JPM",
    ]
    assert [
        item.recommendation
        for item in result.recommendations
    ] == [
        "BUY",
        "WATCH",
    ]