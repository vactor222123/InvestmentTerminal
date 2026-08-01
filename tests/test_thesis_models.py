"""
Tests for investment thesis models.
"""

import json
from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.thesis_models import (
    InvestmentThesis,
    PortfolioThesisResult,
)
from tests.test_recommendation_models import (
    create_recommendation,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    15,
    0,
    tzinfo=timezone.utc,
)


def create_thesis(
    *,
    rank: int = 1,
    symbol: str = "MSFT",
    recommendation: str = "BUY",
) -> InvestmentThesis:
    return InvestmentThesis(
        recommendation=create_recommendation(
            rank=rank,
            symbol=symbol,
            recommendation=recommendation,
        ),
        headline=(
            f"{symbol} presents a strong "
            "investment profile."
        ),
        thesis=(
            f"{symbol} combines strong business quality "
            "with a favorable analytical score."
        ),
        strengths=(
            "Business quality is excellent.",
            "Financial health is strong.",
        ),
        risks=(
            "Valuation is elevated.",
        ),
        action=(
            "Consider gradual position accumulation "
            "while monitoring valuation."
        ),
    )


def test_thesis_exposes_recommendation_values() -> None:
    thesis = create_thesis()

    assert thesis.rank == 1
    assert thesis.symbol == "MSFT"
    assert thesis.currency == "USD"
    assert thesis.recommendation_label == "BUY"
    assert thesis.overall_score == pytest.approx(
        77.41
    )
    assert thesis.confidence_score == pytest.approx(
        96.72
    )
    assert thesis.risk_level == "MEDIUM"


def test_thesis_normalizes_text_fields() -> None:
    thesis = InvestmentThesis(
        recommendation=create_recommendation(),
        headline="  Strong candidate.  ",
        thesis="  The business remains strong.  ",
        strengths=(
            "Strong profitability.",
        ),
        risks=(),
        action="  Monitor valuation.  ",
    )

    assert thesis.headline == "Strong candidate."
    assert thesis.thesis == (
        "The business remains strong."
    )
    assert thesis.action == "Monitor valuation."


def test_thesis_rejects_invalid_recommendation() -> None:
    with pytest.raises(
        TypeError,
        match="CandidateRecommendation",
    ):
        InvestmentThesis(
            recommendation=None,
            headline="Strong candidate.",
            thesis="The business remains strong.",
            strengths=(
                "Strong profitability.",
            ),
            risks=(),
            action="Monitor valuation.",
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "headline",
        "thesis",
        "action",
    ],
)
def test_thesis_rejects_empty_text(
    field_name,
) -> None:
    values = {
        "headline": "Strong candidate.",
        "thesis": "The business remains strong.",
        "action": "Monitor valuation.",
    }
    values[field_name] = " "

    with pytest.raises(
        ValueError,
        match=field_name,
    ):
        InvestmentThesis(
            recommendation=create_recommendation(),
            headline=values["headline"],
            thesis=values["thesis"],
            strengths=(
                "Strong profitability.",
            ),
            risks=(),
            action=values["action"],
        )


def test_thesis_requires_strengths() -> None:
    with pytest.raises(
        ValueError,
        match="strengths must not be empty",
    ):
        InvestmentThesis(
            recommendation=create_recommendation(),
            headline="Strong candidate.",
            thesis="The business remains strong.",
            strengths=(),
            risks=(),
            action="Monitor valuation.",
        )


def test_thesis_requires_tuple_collections() -> None:
    with pytest.raises(
        TypeError,
        match="strengths must be a tuple",
    ):
        InvestmentThesis(
            recommendation=create_recommendation(),
            headline="Strong candidate.",
            thesis="The business remains strong.",
            strengths=[
                "Strong profitability.",
            ],
            risks=(),
            action="Monitor valuation.",
        )


def test_portfolio_thesis_calculates_properties() -> None:
    result = PortfolioThesisResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        theses=(
            create_thesis(
                rank=1,
                symbol="GOOGL",
                recommendation="STRONG_BUY",
            ),
            create_thesis(
                rank=2,
                symbol="MSFT",
                recommendation="BUY",
            ),
            create_thesis(
                rank=3,
                symbol="AAPL",
                recommendation="ACCUMULATE",
            ),
        ),
    )

    assert result.universe_size == 3
    assert result.top_thesis.symbol == "GOOGL"
    assert (
        result.top_thesis.recommendation_label
        == "STRONG_BUY"
    )


def test_portfolio_thesis_rejects_duplicate_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="unique symbols",
    ):
        PortfolioThesisResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            theses=(
                create_thesis(
                    rank=1,
                    symbol="MSFT",
                ),
                create_thesis(
                    rank=2,
                    symbol="MSFT",
                ),
            ),
        )


def test_portfolio_thesis_requires_consecutive_ranks() -> None:
    with pytest.raises(
        ValueError,
        match="consecutive",
    ):
        PortfolioThesisResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            theses=(
                create_thesis(
                    rank=1,
                    symbol="MSFT",
                ),
                create_thesis(
                    rank=3,
                    symbol="AAPL",
                ),
            ),
        )


def test_portfolio_thesis_rejects_empty_collection() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        PortfolioThesisResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            theses=(),
        )


def test_portfolio_thesis_is_json_serializable() -> None:
    result = PortfolioThesisResult(
        schema_version=" 1.0 ",
        generated_at=GENERATED_AT,
        theses=(
            create_thesis(
                rank=1,
                symbol="GOOGL",
                recommendation="STRONG_BUY",
            ),
            create_thesis(
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
    assert '"headline"' in serialized
    assert '"action"' in serialized