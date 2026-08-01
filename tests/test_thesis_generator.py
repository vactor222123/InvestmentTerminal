"""
Tests for InvestmentThesisGenerator.
"""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
    PortfolioRecommendationResult,
)
from investment_terminal.portfolio.thesis_generator import (
    InvestmentThesisGenerator,
)
from tests.test_recommendation_models import (
    create_recommendation,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    16,
    0,
    tzinfo=timezone.utc,
)


def create_custom_recommendation(
    *,
    rank: int = 1,
    symbol: str = "MSFT",
    recommendation: str = "BUY",
    risk_level: str = "LOW",
    technical_condition: str = "STRONG",
) -> CandidateRecommendation:
    base = create_recommendation(
        rank=rank,
        symbol=symbol,
        recommendation=recommendation,
    )

    decision = base.candidate.decision

    quality = replace(
        decision.quality,
        risk_level=risk_level,
        technical_condition=technical_condition,
    )

    updated_decision = replace(
        decision,
        quality=quality,
    )

    updated_candidate = replace(
        base.candidate,
        decision=updated_decision,
    )

    return replace(
        base,
        candidate=updated_candidate,
    )


def create_result(
    *recommendations: CandidateRecommendation,
) -> PortfolioRecommendationResult:
    return PortfolioRecommendationResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        recommendations=tuple(
            recommendations
        ),
    )


def test_generate_creates_thesis_for_each_recommendation() -> None:
    recommendation_result = create_result(
        create_custom_recommendation(
            rank=1,
            symbol="GOOGL",
            recommendation="STRONG_BUY",
        ),
        create_custom_recommendation(
            rank=2,
            symbol="MSFT",
            recommendation="BUY",
        ),
        create_custom_recommendation(
            rank=3,
            symbol="AAPL",
            recommendation="ACCUMULATE",
        ),
    )

    result = InvestmentThesisGenerator().generate(
        recommendation_result,
        generated_at=GENERATED_AT,
    )

    assert result.universe_size == 3

    assert [
        thesis.symbol
        for thesis in result.theses
    ] == [
        "GOOGL",
        "MSFT",
        "AAPL",
    ]

    assert [
        thesis.rank
        for thesis in result.theses
    ] == [
        1,
        2,
        3,
    ]


@pytest.mark.parametrize(
    ("recommendation", "expected_text"),
    [
        (
            "STRONG_BUY",
            "strongest investment profiles",
        ),
        (
            "BUY",
            "strong investment profile",
        ),
        (
            "ACCUMULATE",
            "position building should remain gradual",
        ),
        (
            "HOLD",
            "balanced investment profile",
        ),
        (
            "WATCH",
            "requires further monitoring",
        ),
        (
            "AVOID",
            "unfavorable risk-reward profile",
        ),
    ],
)
def test_generate_builds_label_specific_headline(
    recommendation,
    expected_text,
) -> None:
    recommendation_result = create_result(
        create_custom_recommendation(
            recommendation=recommendation,
        )
    )

    result = InvestmentThesisGenerator().generate(
        recommendation_result,
        generated_at=GENERATED_AT,
    )

    assert (
        expected_text
        in result.top_thesis.headline
    )


def test_generate_builds_complete_thesis_text() -> None:
    recommendation_result = create_result(
        create_custom_recommendation(
            symbol="GOOGL",
            recommendation="BUY",
        )
    )

    result = InvestmentThesisGenerator().generate(
        recommendation_result,
        generated_at=GENERATED_AT,
    )

    thesis = result.top_thesis.thesis

    assert "GOOGL ranks #1" in thesis
    assert "overall score" in thesis
    assert "Business quality" in thesis
    assert "Valuation is" in thesis
    assert "analytical recommendation is BUY" in thesis
    assert "confidence score" in thesis


def test_generate_combines_strengths_without_duplicates() -> None:
    base = create_custom_recommendation(
        recommendation="BUY",
    )

    recommendation = replace(
        base,
        rationale=(
            "Revenue growth is strong.",
            "Business quality is excellent.",
        ),
    )

    decision = replace(
        recommendation.candidate.decision,
        positive_factors=(
            "Revenue growth is strong.",
            "Operating margin is strong.",
        ),
    )

    candidate = replace(
        recommendation.candidate,
        decision=decision,
    )

    recommendation = replace(
        recommendation,
        candidate=candidate,
    )

    result = InvestmentThesisGenerator().generate(
        create_result(recommendation),
        generated_at=GENERATED_AT,
    )

    assert result.top_thesis.strengths == (
        "Revenue growth is strong.",
        "Business quality is excellent.",
        "Operating margin is strong.",
    )


def test_generate_combines_risks_without_duplicates() -> None:
    base = create_custom_recommendation(
        recommendation="BUY",
    )

    recommendation = replace(
        base,
        cautions=(
            "Valuation is elevated.",
        ),
    )

    decision = replace(
        recommendation.candidate.decision,
        risk_factors=(
            "Valuation is elevated.",
            "RSI indicates an overbought market.",
        ),
    )

    candidate = replace(
        recommendation.candidate,
        decision=decision,
    )

    recommendation = replace(
        recommendation,
        candidate=candidate,
    )

    result = InvestmentThesisGenerator().generate(
        create_result(recommendation),
        generated_at=GENERATED_AT,
    )

    assert result.top_thesis.risks == (
        "Valuation is elevated.",
        "RSI indicates an overbought market.",
    )


def test_strong_buy_extended_uses_staged_action() -> None:
    result = InvestmentThesisGenerator().generate(
        create_result(
            create_custom_recommendation(
                recommendation="STRONG_BUY",
                technical_condition=(
                    "POSITIVE BUT EXTENDED"
                ),
            )
        ),
        generated_at=GENERATED_AT,
    )

    assert (
        "staged position accumulation"
        in result.top_thesis.action
    )
    assert (
        "favorable technical entry"
        in result.top_thesis.action
    )


def test_buy_medium_risk_uses_smaller_entries() -> None:
    result = InvestmentThesisGenerator().generate(
        create_result(
            create_custom_recommendation(
                recommendation="BUY",
                risk_level="MEDIUM",
            )
        ),
        generated_at=GENERATED_AT,
    )

    assert (
        "smaller entries"
        in result.top_thesis.action
    )
    assert (
        "risk monitoring"
        in result.top_thesis.action
    )


@pytest.mark.parametrize(
    ("recommendation", "expected_text"),
    [
        (
            "ACCUMULATE",
            "multiple entries",
        ),
        (
            "HOLD",
            "active watchlist",
        ),
        (
            "WATCH",
            "Do not prioritize a new position yet",
        ),
        (
            "AVOID",
            "Avoid initiating a new position",
        ),
    ],
)
def test_generate_builds_label_specific_action(
    recommendation,
    expected_text,
) -> None:
    result = InvestmentThesisGenerator().generate(
        create_result(
            create_custom_recommendation(
                recommendation=recommendation,
            )
        ),
        generated_at=GENERATED_AT,
    )

    assert (
        expected_text
        in result.top_thesis.action
    )


def test_generate_uses_generated_at() -> None:
    result = InvestmentThesisGenerator().generate(
        create_result(
            create_custom_recommendation()
        ),
        generated_at=GENERATED_AT,
    )

    assert result.generated_at == GENERATED_AT
    assert result.schema_version == "1.0"


def test_generate_rejects_invalid_result() -> None:
    with pytest.raises(
        TypeError,
        match="PortfolioRecommendationResult",
    ):
        InvestmentThesisGenerator().generate(
            None
        )


def test_generate_rejects_invalid_generated_at() -> None:
    recommendation_result = create_result(
        create_custom_recommendation()
    )

    with pytest.raises(
        TypeError,
        match="generated_at",
    ):
        InvestmentThesisGenerator().generate(
            recommendation_result,
            generated_at="2026-08-01",
        )