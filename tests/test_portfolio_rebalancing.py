import pytest

from investment_terminal.portfolio.portfolio_policy_gap_models import (
    PortfolioPolicyGapItem,
    PortfolioPolicyGapResult,
)
from investment_terminal.portfolio.portfolio_rebalancing import (
    PortfolioRebalancingEvidenceBuilder,
    PortfolioRebalancingItem,
)


def item(
    key: str, current_amount: float, target_amount: float
) -> PortfolioPolicyGapItem:
    total = 10000.0
    current_weight = current_amount / total
    target_weight = target_amount / total
    return PortfolioPolicyGapItem(
        key,
        current_amount,
        current_weight,
        target_amount,
        target_weight,
        target_amount - current_amount,
        target_weight - current_weight,
    )


def gaps() -> PortfolioPolicyGapResult:
    return PortfolioPolicyGapResult(
        "Personal",
        "EUR",
        10000.0,
        (
            item("CORE_LONG_TERM", 7000.0, 8000.0),
            item("TACTICAL_TOTAL", 1200.0, 1000.0),
            item("CASH_RESERVE", 1800.0, 1000.0),
        ),
    )


def test_builds_non_executable_rebalancing_evidence() -> None:
    evidence = PortfolioRebalancingEvidenceBuilder.build(gaps(), tolerance_weight=0.01)
    assert [entry.action for entry in evidence.items] == [
        "INCREASE",
        "REDUCE",
        "REDUCE",
    ]
    assert evidence.total_increase_amount == 1000.0
    assert evidence.total_reduce_amount == 1000.0
    assert evidence.transferable_amount == 1000.0
    assert evidence.requires_review is True
    assert evidence.to_dict()["execution_authorized"] is False


def test_tolerance_is_explicit_and_inclusive_for_hold() -> None:
    evidence = PortfolioRebalancingEvidenceBuilder.build(gaps(), tolerance_weight=0.10)
    assert [entry.action for entry in evidence.items] == ["HOLD", "HOLD", "HOLD"]
    assert evidence.transferable_amount == 0
    assert evidence.requires_review is False


@pytest.mark.parametrize("value", [-0.01, 1.01, True, float("inf")])
def test_rejects_invalid_tolerance(value: object) -> None:
    with pytest.raises(ValueError, match="tolerance_weight"):
        PortfolioRebalancingEvidenceBuilder.build(
            gaps(), tolerance_weight=value  # type: ignore[arg-type]
        )


def test_unbalanced_gaps_expose_only_fundable_transfer() -> None:
    result = PortfolioPolicyGapResult(
        "Personal",
        "EUR",
        10000.0,
        (
            item("CORE_LONG_TERM", 6500.0, 8000.0),
            item("TACTICAL_TOTAL", 1200.0, 1000.0),
            item("CASH_RESERVE", 1300.0, 1000.0),
        ),
    )
    evidence = PortfolioRebalancingEvidenceBuilder.build(result, tolerance_weight=0.01)
    assert evidence.total_increase_amount == 1500.0
    assert evidence.total_reduce_amount == 500.0
    assert evidence.transferable_amount == 500.0


def test_item_rejects_action_that_conflicts_with_gap() -> None:
    with pytest.raises(ValueError, match="positive gap_weight"):
        PortfolioRebalancingItem(
            "CORE_LONG_TERM",
            8000.0,
            0.8,
            7000.0,
            0.7,
            -1000.0,
            -0.1,
            "INCREASE",
            1000.0,
        )


def test_builder_requires_policy_gap_result() -> None:
    with pytest.raises(TypeError, match="PortfolioPolicyGapResult"):
        PortfolioRebalancingEvidenceBuilder.build(  # type: ignore[arg-type]
            object(), tolerance_weight=0.01
        )
