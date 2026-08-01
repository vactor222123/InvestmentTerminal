"""
Tests for PortfolioAllocationEngine.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.allocation_engine import (
    PortfolioAllocationEngine,
)
from investment_terminal.portfolio.allocation_models import (
    AllocationConstraints,
)
from investment_terminal.portfolio.recommendation_models import (
    PortfolioRecommendationResult,
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


def create_recommendation_result(
    labels=(
        "BUY",
        "BUY",
        "ACCUMULATE",
        "ACCUMULATE",
        "HOLD",
    ),
) -> PortfolioRecommendationResult:
    symbols = (
        "GOOGL",
        "NVDA",
        "MSFT",
        "AAPL",
        "META",
    )

    return PortfolioRecommendationResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        recommendations=tuple(
            create_recommendation(
                rank=index,
                symbol=symbol,
                recommendation=label,
            )
            for index, (
                symbol,
                label,
            ) in enumerate(
                zip(
                    symbols,
                    labels,
                    strict=True,
                ),
                start=1,
            )
        ),
    )


def test_allocate_builds_balanced_portfolio() -> None:
    result = PortfolioAllocationEngine().allocate(
        create_recommendation_result(),
        total_capital=100_000.0,
        profile=" balanced ",
        generated_at=GENERATED_AT,
    )

    assert result.schema_version == "1.0"
    assert result.generated_at == GENERATED_AT
    assert result.constraints.profile == "BALANCED"
    assert result.total_capital == 100_000.0
    assert result.invested_amount == 90_000.0
    assert result.cash_amount == 10_000.0
    assert result.invested_weight == 0.90
    assert result.universe_size == 5

    assert [
        position.symbol
        for position in result.positions
    ] == [
        "GOOGL",
        "NVDA",
        "MSFT",
        "AAPL",
        "META",
    ]

    assert sum(
        position.target_weight
        for position in result.positions
    ) == pytest.approx(
        0.90
    )

    assert all(
        position.target_weight <= 0.30
        for position in result.positions
    )


def test_higher_ranked_buy_receives_more_than_hold() -> None:
    result = PortfolioAllocationEngine().allocate(
        create_recommendation_result(),
        total_capital=100_000.0,
        profile="BALANCED",
        generated_at=GENERATED_AT,
    )

    weights = {
        position.symbol: position.target_weight
        for position in result.positions
    }

    assert weights["GOOGL"] > weights["META"]
    assert weights["NVDA"] > weights["META"]


def test_watch_and_avoid_receive_zero_weight() -> None:
    result = PortfolioAllocationEngine().allocate(
        create_recommendation_result(
            labels=(
                "BUY",
                "BUY",
                "ACCUMULATE",
                "WATCH",
                "AVOID",
            )
        ),
        total_capital=100_000.0,
        profile="GROWTH",
        generated_at=GENERATED_AT,
        constraints=AllocationConstraints(
            profile="GROWTH",
            minimum_position_weight=0.05,
            maximum_position_weight=0.40,
            cash_reserve_weight=0.05,
        ),
    )

    weights = {
        position.symbol: position.target_weight
        for position in result.positions
    }

    assert weights["AAPL"] == 0.0
    assert weights["META"] == 0.0
    assert (
        result.positions[3]
        .explanation
        .endswith("WATCH.")
    )
    assert (
        result.positions[4]
        .explanation
        .endswith("AVOID.")
    )


def test_conservative_profile_keeps_more_cash() -> None:
    engine = PortfolioAllocationEngine()
    recommendations = (
        create_recommendation_result()
    )

    conservative = engine.allocate(
        recommendations,
        total_capital=100_000.0,
        profile="CONSERVATIVE",
        generated_at=GENERATED_AT,
    )
    growth = engine.allocate(
        recommendations,
        total_capital=100_000.0,
        profile="GROWTH",
        generated_at=GENERATED_AT,
    )

    assert conservative.cash_weight == 0.20
    assert conservative.cash_amount == 20_000.0
    assert growth.cash_weight == 0.05
    assert growth.cash_amount == 5_000.0


def test_allocate_respects_custom_constraints() -> None:
    constraints = AllocationConstraints(
        profile="BALANCED",
        minimum_position_weight=0.10,
        maximum_position_weight=0.25,
        cash_reserve_weight=0.10,
    )

    result = PortfolioAllocationEngine().allocate(
        create_recommendation_result(),
        total_capital=50_000.0,
        profile="BALANCED",
        generated_at=GENERATED_AT,
        constraints=constraints,
    )

    assert result.constraints is constraints
    assert all(
        position.target_weight >= 0.10
        for position in result.positions
    )
    assert all(
        position.target_weight <= 0.25
        for position in result.positions
    )


def test_allocation_score_uses_recommendation_label() -> None:
    recommendations = (
        create_recommendation_result(
            labels=(
                "STRONG_BUY",
                "BUY",
                "ACCUMULATE",
                "HOLD",
                "HOLD",
            )
        )
    )

    result = PortfolioAllocationEngine().allocate(
        recommendations,
        total_capital=100_000.0,
        profile="BALANCED",
        generated_at=GENERATED_AT,
    )

    scores = [
        position.allocation_score
        for position in result.positions
    ]

    assert scores[0] > scores[1]
    assert scores[1] > scores[2]
    assert scores[2] > scores[3]


def test_allocate_rejects_infeasible_maximum() -> None:
    constraints = AllocationConstraints(
        profile="BALANCED",
        minimum_position_weight=0.05,
        maximum_position_weight=0.15,
        cash_reserve_weight=0.10,
    )

    with pytest.raises(
        ValueError,
        match="maximum_position_weight",
    ):
        PortfolioAllocationEngine().allocate(
            create_recommendation_result(),
            total_capital=100_000.0,
            profile="BALANCED",
            generated_at=GENERATED_AT,
            constraints=constraints,
        )


def test_allocate_rejects_infeasible_minimum() -> None:
    constraints = AllocationConstraints(
        profile="BALANCED",
        minimum_position_weight=0.20,
        maximum_position_weight=0.30,
        cash_reserve_weight=0.10,
    )

    with pytest.raises(
        ValueError,
        match="minimum_position_weight",
    ):
        PortfolioAllocationEngine().allocate(
            create_recommendation_result(),
            total_capital=100_000.0,
            profile="BALANCED",
            generated_at=GENERATED_AT,
            constraints=constraints,
        )


def test_allocate_rejects_currency_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="currencies",
    ):
        PortfolioAllocationEngine().allocate(
            create_recommendation_result(),
            total_capital=100_000.0,
            profile="BALANCED",
            currency="EUR",
            generated_at=GENERATED_AT,
        )


def test_allocate_rejects_profile_constraint_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="profile must match",
    ):
        PortfolioAllocationEngine().allocate(
            create_recommendation_result(),
            total_capital=100_000.0,
            profile="GROWTH",
            generated_at=GENERATED_AT,
            constraints=AllocationConstraints(
                profile="BALANCED",
                minimum_position_weight=0.05,
                maximum_position_weight=0.30,
                cash_reserve_weight=0.10,
            ),
        )


def test_allocate_requires_eligible_candidate() -> None:
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        PortfolioAllocationEngine().allocate(
            create_recommendation_result(
                labels=(
                    "WATCH",
                    "WATCH",
                    "AVOID",
                    "AVOID",
                    "WATCH",
                )
            ),
            total_capital=100_000.0,
            profile="BALANCED",
            generated_at=GENERATED_AT,
        )


def test_allocate_rejects_naive_generated_at() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        PortfolioAllocationEngine().allocate(
            create_recommendation_result(),
            total_capital=100_000.0,
            profile="BALANCED",
            generated_at=datetime(
                2026,
                8,
                1,
                16,
                0,
            ),
        )


def test_allocate_result_is_json_ready() -> None:
    result = PortfolioAllocationEngine().allocate(
        create_recommendation_result(),
        total_capital=100_000.0,
        profile="BALANCED",
        generated_at=GENERATED_AT,
    )

    payload = result.to_dict()

    assert payload["profile"] == "BALANCED"
    assert payload["currency"] == "USD"
    assert payload["total_capital"] == 100_000.0
    assert payload["cash_amount"] == 10_000.0
    assert payload["top_symbol"] in {
        "GOOGL",
        "NVDA",
        "MSFT",
        "AAPL",
        "META",
    }
    assert len(payload["positions"]) == 5