"""
Tests for portfolio-allocation models.
"""

import json
from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.allocation_models import (
    AllocationConstraints,
    PortfolioAllocationPosition,
    PortfolioAllocationResult,
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


def create_constraints() -> AllocationConstraints:
    return AllocationConstraints(
        profile=" balanced ",
        minimum_position_weight=0.05,
        maximum_position_weight=0.40,
        cash_reserve_weight=0.10,
    )


def create_position(
    *,
    rank: int,
    symbol: str,
    target_weight: float,
    total_capital: float = 100_000.0,
) -> PortfolioAllocationPosition:
    recommendation = create_recommendation(
        rank=rank,
        symbol=symbol,
        recommendation=(
            "BUY"
            if rank <= 2
            else "ACCUMULATE"
        ),
    )

    return PortfolioAllocationPosition(
        recommendation=recommendation,
        target_weight=target_weight,
        target_amount=(
            total_capital * target_weight
        ),
        allocation_score=(
            100.0 - rank
        ),
        explanation=(
            f"{symbol} receives a target weight "
            "based on score and risk."
        ),
    )


def create_result() -> PortfolioAllocationResult:
    return PortfolioAllocationResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        total_capital=100_000.0,
        currency=" usd ",
        constraints=create_constraints(),
        positions=(
            create_position(
                rank=1,
                symbol="GOOGL",
                target_weight=0.35,
            ),
            create_position(
                rank=2,
                symbol="NVDA",
                target_weight=0.30,
            ),
            create_position(
                rank=3,
                symbol="MSFT",
                target_weight=0.25,
            ),
        ),
        cash_amount=10_000.0,
    )


def test_constraints_normalize_profile() -> None:
    constraints = create_constraints()

    assert constraints.profile == "BALANCED"
    assert constraints.investable_weight == 0.90


def test_constraints_reject_invalid_profile() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported allocation profile",
    ):
        AllocationConstraints(
            profile="AGGRESSIVE",
            minimum_position_weight=0.05,
            maximum_position_weight=0.40,
            cash_reserve_weight=0.10,
        )


def test_constraints_reject_minimum_above_maximum() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed",
    ):
        AllocationConstraints(
            profile="BALANCED",
            minimum_position_weight=0.50,
            maximum_position_weight=0.40,
            cash_reserve_weight=0.10,
        )


def test_position_exposes_recommendation_context() -> None:
    position = create_position(
        rank=1,
        symbol="GOOGL",
        target_weight=0.35,
    )

    assert position.rank == 1
    assert position.symbol == "GOOGL"
    assert position.currency == "USD"
    assert position.recommendation_label == "BUY"
    assert position.target_percent == 35.0
    assert position.target_amount == 35_000.0


def test_position_rejects_weight_above_one() -> None:
    recommendation = create_recommendation(
        rank=1,
        symbol="GOOGL",
        recommendation="BUY",
    )

    with pytest.raises(
        ValueError,
        match="must not exceed one",
    ):
        PortfolioAllocationPosition(
            recommendation=recommendation,
            target_weight=1.01,
            target_amount=101_000.0,
            allocation_score=99.0,
            explanation="Invalid overweight position.",
        )


def test_result_combines_positions_and_cash() -> None:
    result = create_result()

    assert result.schema_version == "1.0"
    assert result.currency == "USD"
    assert result.universe_size == 3
    assert result.invested_weight == 0.90
    assert result.invested_amount == 90_000.0
    assert result.cash_weight == 0.10
    assert result.cash_amount == 10_000.0
    assert result.top_position.symbol == "GOOGL"


def test_result_is_json_serializable() -> None:
    result = create_result()

    payload = result.to_dict()
    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert payload["profile"] == "BALANCED"
    assert payload["total_capital"] == 100_000.0
    assert payload["invested_amount"] == 90_000.0
    assert payload["cash_amount"] == 10_000.0
    assert payload["top_symbol"] == "GOOGL"
    assert len(payload["positions"]) == 3
    assert '"target_percent": 35.0' in serialized


def test_result_rejects_incorrect_weight_total() -> None:
    with pytest.raises(
        ValueError,
        match="investable portfolio weight",
    ):
        PortfolioAllocationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            total_capital=100_000.0,
            currency="USD",
            constraints=create_constraints(),
            positions=(
                create_position(
                    rank=1,
                    symbol="GOOGL",
                    target_weight=0.30,
                ),
                create_position(
                    rank=2,
                    symbol="NVDA",
                    target_weight=0.30,
                ),
                create_position(
                    rank=3,
                    symbol="MSFT",
                    target_weight=0.20,
                ),
            ),
            cash_amount=10_000.0,
        )


def test_result_rejects_position_above_maximum() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_position_weight",
    ):
        PortfolioAllocationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            total_capital=100_000.0,
            currency="USD",
            constraints=create_constraints(),
            positions=(
                create_position(
                    rank=1,
                    symbol="GOOGL",
                    target_weight=0.45,
                ),
                create_position(
                    rank=2,
                    symbol="NVDA",
                    target_weight=0.25,
                ),
                create_position(
                    rank=3,
                    symbol="MSFT",
                    target_weight=0.20,
                ),
            ),
            cash_amount=10_000.0,
        )


def test_result_rejects_position_below_minimum() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_position_weight",
    ):
        PortfolioAllocationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            total_capital=100_000.0,
            currency="USD",
            constraints=create_constraints(),
            positions=(
                create_position(
                    rank=1,
                    symbol="GOOGL",
                    target_weight=0.30,
                ),
                create_position(
                    rank=2,
                    symbol="NVDA",
                    target_weight=0.28,
                ),
                create_position(
                    rank=3,
                    symbol="MSFT",
                    target_weight=0.28,
                ),
                create_position(
                    rank=4,
                    symbol="AAPL",
                    target_weight=0.04,
                ),
            ),
            cash_amount=10_000.0,
        )


def test_result_rejects_incorrect_target_amount() -> None:
    recommendation = create_recommendation(
        rank=1,
        symbol="GOOGL",
        recommendation="BUY",
    )

    incorrect_position = PortfolioAllocationPosition(
        recommendation=recommendation,
        target_weight=0.35,
        target_amount=34_000.0,
        allocation_score=99.0,
        explanation="Incorrect amount for test.",
    )

    with pytest.raises(
        ValueError,
        match="target_amount",
    ):
        PortfolioAllocationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            total_capital=100_000.0,
            currency="USD",
            constraints=AllocationConstraints(
                profile="BALANCED",
                minimum_position_weight=0.05,
                maximum_position_weight=0.40,
                cash_reserve_weight=0.65,
            ),
            positions=(
                incorrect_position,
            ),
            cash_amount=65_000.0,
        )


def test_result_rejects_incorrect_cash_amount() -> None:
    with pytest.raises(
        ValueError,
        match="cash_amount",
    ):
        PortfolioAllocationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            total_capital=100_000.0,
            currency="USD",
            constraints=create_constraints(),
            positions=(
                create_position(
                    rank=1,
                    symbol="GOOGL",
                    target_weight=0.35,
                ),
                create_position(
                    rank=2,
                    symbol="NVDA",
                    target_weight=0.30,
                ),
                create_position(
                    rank=3,
                    symbol="MSFT",
                    target_weight=0.25,
                ),
            ),
            cash_amount=9_000.0,
        )


def test_result_rejects_duplicate_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="unique symbols",
    ):
        PortfolioAllocationResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            total_capital=100_000.0,
            currency="USD",
            constraints=create_constraints(),
            positions=(
                create_position(
                    rank=1,
                    symbol="GOOGL",
                    target_weight=0.45,
                ),
                create_position(
                    rank=2,
                    symbol="GOOGL",
                    target_weight=0.45,
                ),
            ),
            cash_amount=10_000.0,
        )