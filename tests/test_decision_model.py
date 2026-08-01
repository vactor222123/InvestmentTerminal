"""
Tests for structured decision models.
"""

import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from investment_terminal.decision_engine.decision_model import (
    DecisionConfidence,
    DecisionQualitySummary,
    DecisionResult,
    DecisionScoreSummary,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_result() -> DecisionResult:
    return DecisionResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        symbol=" msft ",
        currency=" usd ",
        scores=DecisionScoreSummary(
            technical=65.0,
            fundamental=85.68,
            overall=77.41,
            technical_weight=0.4,
            fundamental_weight=0.6,
        ),
        quality=DecisionQualitySummary(
            business_quality="excellent",
            financial_health="strong",
            growth="strong",
            valuation="fair",
            technical_condition="positive",
            risk_level="medium",
        ),
        confidence=DecisionConfidence(
            score=98.22,
            classification="very high",
            technical_data_quality=100.0,
            fundamental_data_quality=96.43,
            missing_data_penalty=1.78,
        ),
        classification="strong",
        positive_factors=(
            "Revenue growth is strong.",
            "Long-term price trend is positive.",
        ),
        risk_factors=(
            "The stock is technically overbought.",
        ),
        missing_data=(
            "return_on_invested_capital",
        ),
        summary=(
            "High-quality business with strong growth, "
            "but short-term technical conditions are extended."
        ),
    )


def test_decision_result_normalizes_text() -> None:
    result = create_result()

    assert result.symbol == "MSFT"
    assert result.currency == "USD"
    assert result.classification == "STRONG"

    assert (
        result.quality.business_quality
        == "EXCELLENT"
    )
    assert (
        result.confidence.classification
        == "VERY HIGH"
    )


def test_decision_result_is_json_serializable() -> None:
    result = create_result()

    payload = result.to_dict()
    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert '"symbol": "MSFT"' in serialized
    assert (
        payload["generated_at"]
        == "2026-08-01T12:00:00+00:00"
    )
    assert isinstance(
        payload["positive_factors"],
        list,
    )
    assert isinstance(
        payload["missing_data"],
        list,
    )


def test_score_summary_rejects_invalid_score() -> None:
    with pytest.raises(
        ValueError,
        match="between 0 and 100",
    ):
        replace(
            create_result().scores,
            overall=101.0,
        )


def test_score_summary_requires_weights_to_sum_to_one() -> None:
    with pytest.raises(
        ValueError,
        match="sum to 1.0",
    ):
        DecisionScoreSummary(
            technical=60.0,
            fundamental=80.0,
            overall=70.0,
            technical_weight=0.7,
            fundamental_weight=0.7,
        )


@pytest.mark.parametrize(
    "weight",
    [
        -0.1,
        1.1,
        float("nan"),
        True,
    ],
)
def test_score_summary_rejects_invalid_weight(
    weight,
) -> None:
    with pytest.raises(ValueError):
        DecisionScoreSummary(
            technical=60.0,
            fundamental=80.0,
            overall=70.0,
            technical_weight=weight,
            fundamental_weight=1.0,
        )


def test_confidence_rejects_invalid_score() -> None:
    with pytest.raises(
        ValueError,
        match="between 0 and 100",
    ):
        replace(
            create_result().confidence,
            score=-1.0,
        )


def test_quality_rejects_empty_value() -> None:
    with pytest.raises(
        ValueError,
        match="business_quality",
    ):
        replace(
            create_result().quality,
            business_quality="   ",
        )


def test_result_rejects_non_tuple_factors() -> None:
    with pytest.raises(
        TypeError,
        match="positive_factors",
    ):
        replace(
            create_result(),
            positive_factors=[
                "Invalid list"
            ],
        )


def test_result_rejects_empty_summary() -> None:
    with pytest.raises(
        ValueError,
        match="summary",
    ):
        replace(
            create_result(),
            summary="   ",
        )