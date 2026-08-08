"""
Tests for canonical historical snapshot comparison models.
"""

from dataclasses import FrozenInstanceError

import pytest

from investment_terminal.history.historical_comparison_models import (
    DeploymentChange,
    HoldingChange,
    PortfolioSummaryChange,
    RecommendationChange,
    ScalarChange,
    SnapshotComparison,
)


FIRST_ID = "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
SECOND_ID = "f9b7adca-2f2b-47a4-901d-05ca37c445df"


def zero_change() -> ScalarChange:
    return ScalarChange.between(
        1.0,
        1.0,
    )


def test_scalar_change_computes_safe_deltas() -> None:
    change = ScalarChange.between(
        100.0,
        125.0,
    )

    assert change.absolute_change == 25.0
    assert change.percentage_change == 25.0


def test_scalar_change_omits_percentage_from_zero_baseline() -> None:
    change = ScalarChange.between(
        0.0,
        10.0,
    )

    assert change.absolute_change == 10.0
    assert change.percentage_change is None


def test_scalar_change_preserves_absent_value_semantics() -> None:
    assert ScalarChange.between(
        None,
        10.0,
    ).to_dict() == {
        "previous": None,
        "current": 10.0,
        "absolute_change": None,
        "percentage_change": None,
    }


def test_scalar_change_rejects_explicit_percentage_from_zero() -> None:
    with pytest.raises(
        ValueError,
        match="undefined when previous is zero",
    ):
        ScalarChange(
            previous=0.0,
            current=5.0,
            absolute_change=5.0,
            percentage_change=100.0,
        )


def test_holding_change_enforces_added_presence_contract() -> None:
    change = HoldingChange(
        holding_key="WORLD",
        change_type=" added ",
        previous=None,
        current={
            "symbol": "WORLD",
        },
        quantity=ScalarChange.between(
            None,
            5.0,
        ),
        unit_price=ScalarChange.between(
            None,
            100.0,
        ),
        market_value=ScalarChange.between(
            None,
            500.0,
        ),
        weight=ScalarChange.between(
            None,
            0.5,
        ),
    )

    assert change.change_type == "ADDED"

    with pytest.raises(
        ValueError,
        match="ADDED requires",
    ):
        HoldingChange(
            holding_key="WORLD",
            change_type="ADDED",
            previous={
                "symbol": "WORLD",
            },
            current={
                "symbol": "WORLD",
            },
            quantity=zero_change(),
            unit_price=zero_change(),
            market_value=zero_change(),
            weight=zero_change(),
        )


def test_portfolio_summary_change_serializes() -> None:
    summary = PortfolioSummaryChange(
        previous_exists=True,
        current_exists=True,
        base_currency_previous="EUR",
        base_currency_current="EUR",
        source_status_previous="COST_BASIS_ONLY",
        source_status_current="MARKET_VALUE_CONNECTED",
        total_value=ScalarChange.between(
            10000.0,
            11000.0,
        ),
        invested_value=ScalarChange.between(
            9000.0,
            9800.0,
        ),
        cash_value=ScalarChange.between(
            1000.0,
            1200.0,
        ),
        monthly_contribution=ScalarChange.between(
            500.0,
            500.0,
        ),
        cash_weight=ScalarChange.between(
            0.10,
            0.109,
        ),
        invested_weight=ScalarChange.between(
            0.90,
            0.891,
        ),
    )

    assert summary.to_dict()[
        "base_currency_current"
    ] == "EUR"


def test_snapshot_comparison_serializes_nested_changes() -> None:
    recommendation = RecommendationChange(
        recommendation_key="BABA",
        change_type="CHANGED",
        previous={
            "action": "HOLD",
        },
        current={
            "action": "BUY",
        },
        score=ScalarChange.between(
            70.0,
            82.5,
        ),
        confidence=ScalarChange.between(
            0.6,
            0.76,
        ),
    )
    deployment = DeploymentChange(
        deployment_key="BABA",
        change_type="ADDED",
        previous=None,
        current={
            "amount": 600.0,
        },
        amount=ScalarChange.between(
            None,
            600.0,
        ),
        share=ScalarChange.between(
            None,
            0.30,
        ),
    )

    comparison = SnapshotComparison(
        earlier_snapshot_id=FIRST_ID.upper(),
        later_snapshot_id=SECOND_ID,
        compatibility_status=" compatible ",
        portfolio_summary=None,
        holdings=(),
        recommendations=(
            recommendation,
        ),
        deployment=(
            deployment,
        ),
        compatibility_notes=(
            "Same base currency",
        ),
    )

    result = comparison.to_dict()

    assert comparison.earlier_snapshot_id == FIRST_ID
    assert comparison.compatibility_status == "COMPATIBLE"
    assert result[
        "recommendations"
    ][0]["recommendation_key"] == "BABA"
    assert result[
        "deployment"
    ][0]["change_type"] == "ADDED"


def test_snapshot_comparison_rejects_same_snapshot() -> None:
    with pytest.raises(
        ValueError,
        match="must differ",
    ):
        SnapshotComparison(
            earlier_snapshot_id=FIRST_ID,
            later_snapshot_id=FIRST_ID,
            compatibility_status="COMPATIBLE",
            portfolio_summary=None,
            holdings=(),
            recommendations=(),
            deployment=(),
        )


def test_snapshot_comparison_rejects_invalid_compatibility_status() -> None:
    with pytest.raises(
        ValueError,
        match="compatibility_status must be one of",
    ):
        SnapshotComparison(
            earlier_snapshot_id=FIRST_ID,
            later_snapshot_id=SECOND_ID,
            compatibility_status="UNKNOWN",
            portfolio_summary=None,
            holdings=(),
            recommendations=(),
            deployment=(),
        )


def test_models_are_frozen() -> None:
    comparison = SnapshotComparison(
        earlier_snapshot_id=FIRST_ID,
        later_snapshot_id=SECOND_ID,
        compatibility_status="INCOMPATIBLE",
        portfolio_summary=None,
        holdings=(),
        recommendations=(),
        deployment=(),
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        comparison.compatibility_status = "COMPATIBLE"  # type: ignore[misc]
