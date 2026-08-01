"""
Tests for the modular DecisionEngine.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.decision_engine.confidence import (
    ConfidenceEngine,
)
from investment_terminal.decision_engine.decision_engine import (
    DecisionEngine,
)
from investment_terminal.decision_engine.weighting import (
    DecisionWeighting,
    DecisionWeights,
)
from tests.test_analysis_exporter import (
    create_fundamental_score,
    create_fundamental_snapshot,
    create_technical_analysis,
    create_technical_score,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def test_weighting_calculates_overall_score() -> None:
    result = DecisionWeighting.calculate_overall(
        technical_score=65.0,
        fundamental_score=85.68,
        weights=DecisionWeights(
            technical=0.4,
            fundamental=0.6,
        ),
    )

    assert result == pytest.approx(77.41)


def test_decision_engine_builds_result() -> None:
    result = DecisionEngine().evaluate(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    assert result.symbol == "MSFT"
    assert result.currency == "USD"
    assert result.scores.technical == 65.0
    assert result.scores.fundamental == 85.68
    assert result.scores.overall == pytest.approx(
        77.41
    )

    assert result.classification == "STRONG"
    assert result.generated_at == GENERATED_AT

    assert result.quality.business_quality
    assert result.quality.financial_health
    assert result.quality.growth
    assert result.quality.valuation
    assert result.quality.technical_condition
    assert result.quality.risk_level


def test_decision_engine_builds_confidence() -> None:
    result = DecisionEngine().evaluate(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    assert result.confidence.score == pytest.approx(
        96.72,
        abs=0.01,
    )
    assert (
        result.confidence.classification
        == "VERY HIGH"
    )
    assert (
        result.confidence.missing_data_penalty
        == 1.5
    )


def test_decision_engine_prefixes_missing_data() -> None:
    result = DecisionEngine().evaluate(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    assert (
        "fundamental.return_on_invested_capital"
        in result.missing_data
    )


def test_confidence_classification() -> None:
    assert ConfidenceEngine.classify(95) == (
        "VERY HIGH"
    )
    assert ConfidenceEngine.classify(80) == "HIGH"
    assert ConfidenceEngine.classify(65) == (
        "MODERATE"
    )
    assert ConfidenceEngine.classify(45) == "LOW"
    assert ConfidenceEngine.classify(20) == (
        "VERY LOW"
    )


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(
        ValueError,
        match="sum to 1.0",
    ):
        DecisionWeights(
            technical=0.5,
            fundamental=0.6,
        )


def test_decision_engine_rejects_symbol_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="same symbol",
    ):
        DecisionEngine().evaluate(
            technical_analysis=(
                create_technical_analysis()
            ),
            technical_score=(
                create_technical_score(
                    symbol="AAPL"
                )
            ),
            fundamental_snapshot=(
                create_fundamental_snapshot()
            ),
            fundamental_score=(
                create_fundamental_score()
            ),
        )


def test_decision_result_is_json_ready() -> None:
    result = DecisionEngine().evaluate(
        technical_analysis=(
            create_technical_analysis()
        ),
        technical_score=create_technical_score(),
        fundamental_snapshot=(
            create_fundamental_snapshot()
        ),
        fundamental_score=(
            create_fundamental_score()
        ),
        generated_at=GENERATED_AT,
    )

    payload = result.to_dict()

    assert payload["symbol"] == "MSFT"
    assert payload["scores"]["overall"] == (
        pytest.approx(77.41)
    )
    assert isinstance(
        payload["positive_factors"],
        list,
    )
    assert isinstance(
        payload["missing_data"],
        list,
    )