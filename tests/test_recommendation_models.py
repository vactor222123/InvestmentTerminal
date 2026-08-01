"""
Tests for portfolio recommendation models.
"""

import json
from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
    PortfolioRecommendationResult,
)
from tests.test_ranking_models import (
    create_candidate,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    13,
    0,
    tzinfo=timezone.utc,
)


def create_recommendation(
    rank: int = 1,
    symbol: str = "MSFT",
    recommendation: str = "BUY",
) -> CandidateRecommendation:
    return CandidateRecommendation(
        candidate=create_candidate(
            rank=rank,
            symbol=symbol,
        ),
        recommendation=recommendation,
        rationale=(
            "Business quality is excellent.",
            "Overall score is strong.",
        ),
        cautions=(
            "Valuation is elevated.",
        ),
    )


def test_candidate_recommendation_exposes_values() -> None:
    result = create_recommendation(
        recommendation=" strong buy ",
    )

    assert result.rank == 1
    assert result.symbol == "MSFT"
    assert result.currency == "USD"
    assert result.recommendation == "STRONG_BUY"
    assert result.overall_score == pytest.approx(
        77.41
    )
    assert result.confidence_score == pytest.approx(
        96.72
    )
    assert result.risk_level == "MEDIUM"


def test_candidate_recommendation_accepts_spaces() -> None:
    result = create_recommendation(
        recommendation="strong buy",
    )

    assert result.recommendation == "STRONG_BUY"


def test_candidate_recommendation_rejects_invalid_candidate() -> None:
    with pytest.raises(
        TypeError,
        match="RankingCandidate",
    ):
        CandidateRecommendation(
            candidate=None,
            recommendation="BUY",
            rationale=(
                "Strong fundamentals.",
            ),
            cautions=(),
        )


def test_candidate_recommendation_rejects_unknown_label() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported recommendation",
    ):
        create_recommendation(
            recommendation="SELL",
        )


def test_candidate_recommendation_requires_rationale() -> None:
    with pytest.raises(
        ValueError,
        match="rationale must not be empty",
    ):
        CandidateRecommendation(
            candidate=create_candidate(),
            recommendation="BUY",
            rationale=(),
            cautions=(),
        )


def test_candidate_recommendation_requires_tuple_collections() -> None:
    with pytest.raises(
        TypeError,
        match="rationale must be a tuple",
    ):
        CandidateRecommendation(
            candidate=create_candidate(),
            recommendation="BUY",
            rationale=[
                "Strong fundamentals.",
            ],
            cautions=(),
        )


def test_portfolio_result_calculates_properties() -> None:
    result = PortfolioRecommendationResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        recommendations=(
            create_recommendation(
                rank=1,
                symbol="GOOGL",
                recommendation="STRONG_BUY",
            ),
            create_recommendation(
                rank=2,
                symbol="MSFT",
                recommendation="BUY",
            ),
            create_recommendation(
                rank=3,
                symbol="AAPL",
                recommendation="HOLD",
            ),
        ),
    )

    assert result.universe_size == 3
    assert (
        result.top_recommendation.symbol
        == "GOOGL"
    )
    assert (
        result.top_recommendation.recommendation
        == "STRONG_BUY"
    )


def test_portfolio_result_rejects_duplicate_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="unique symbols",
    ):
        PortfolioRecommendationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            recommendations=(
                create_recommendation(
                    rank=1,
                    symbol="MSFT",
                ),
                create_recommendation(
                    rank=2,
                    symbol="MSFT",
                ),
            ),
        )


def test_portfolio_result_requires_consecutive_ranks() -> None:
    with pytest.raises(
        ValueError,
        match="consecutive",
    ):
        PortfolioRecommendationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            recommendations=(
                create_recommendation(
                    rank=1,
                    symbol="MSFT",
                ),
                create_recommendation(
                    rank=3,
                    symbol="AAPL",
                ),
            ),
        )


def test_portfolio_result_rejects_empty_collection() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        PortfolioRecommendationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            recommendations=(),
        )


def test_portfolio_result_is_json_serializable() -> None:
    result = PortfolioRecommendationResult(
        schema_version=" 1.0 ",
        generated_at=GENERATED_AT,
        recommendations=(
            create_recommendation(
                rank=1,
                symbol="GOOGL",
                recommendation="STRONG_BUY",
            ),
            create_recommendation(
                rank=2,
                symbol="MSFT",
                recommendation="BUY",
            ),
        ),
    )

    payload = result.to_dict()

    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert result.schema_version == "1.0"
    assert payload["universe_size"] == 2
    assert payload["top_symbol"] == "GOOGL"
    assert (
        payload["top_recommendation"]
        == "STRONG_BUY"
    )
    assert '"recommendation": "BUY"' in serialized