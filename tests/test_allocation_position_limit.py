"""
Tests for funded-position limits in PortfolioAllocationEngine.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.allocation_engine import (
    PortfolioAllocationEngine,
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
    18,
    0,
    tzinfo=timezone.utc,
)


def create_large_recommendation_result(
    size: int = 30,
) -> PortfolioRecommendationResult:
    labels = (
        "BUY",
        "BUY",
        "ACCUMULATE",
        "ACCUMULATE",
        "HOLD",
    )

    return PortfolioRecommendationResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        recommendations=tuple(
            create_recommendation(
                rank=index,
                symbol=f"T{index:02d}",
                recommendation=labels[
                    min(index - 1, 4)
                ],
            )
            for index in range(
                1,
                size + 1,
            )
        ),
    )


def test_allocate_funds_only_top_n_positions() -> None:
    result = PortfolioAllocationEngine().allocate(
        create_large_recommendation_result(),
        total_capital=100_000.0,
        profile="BALANCED",
        generated_at=GENERATED_AT,
        max_positions=5,
    )

    funded = tuple(
        position
        for position in result.positions
        if position.target_weight > 0
    )
    unfunded = tuple(
        position
        for position in result.positions
        if position.target_weight == 0
    )

    assert len(result.positions) == 30
    assert len(funded) == 5
    assert len(unfunded) == 25
    assert [
        position.rank
        for position in funded
    ] == [1, 2, 3, 4, 5]
    assert sum(
        position.target_weight
        for position in funded
    ) == pytest.approx(0.90)


def test_unfunded_ranked_candidate_has_clear_explanation() -> None:
    result = PortfolioAllocationEngine().allocate(
        create_large_recommendation_result(),
        total_capital=100_000.0,
        profile="BALANCED",
        generated_at=GENERATED_AT,
        max_positions=5,
    )

    assert (
        "outside the selected funded-position limit"
        in result.positions[5].explanation
    )


def test_allocate_without_limit_keeps_existing_behavior() -> None:
    recommendations = create_large_recommendation_result(
        size=5
    )

    result = PortfolioAllocationEngine().allocate(
        recommendations,
        total_capital=100_000.0,
        profile="BALANCED",
        generated_at=GENERATED_AT,
    )

    assert all(
        position.target_weight > 0
        for position in result.positions
    )


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
    ],
)
def test_allocate_rejects_non_positive_max_positions(
    value: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        PortfolioAllocationEngine().allocate(
            create_large_recommendation_result(
                size=5
            ),
            total_capital=100_000.0,
            profile="BALANCED",
            generated_at=GENERATED_AT,
            max_positions=value,
        )


def test_allocate_rejects_non_integer_max_positions() -> None:
    with pytest.raises(
        TypeError,
        match="integer",
    ):
        PortfolioAllocationEngine().allocate(
            create_large_recommendation_result(
                size=5
            ),
            total_capital=100_000.0,
            profile="BALANCED",
            generated_at=GENERATED_AT,
            max_positions=5.0,
        )