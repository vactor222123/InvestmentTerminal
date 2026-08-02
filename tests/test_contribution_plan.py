"""
Tests for contribution planning from portfolio policy gaps.
"""

from investment_terminal.portfolio.contribution_plan_service import (
    ContributionPlanner,
)
from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)
from investment_terminal.portfolio.portfolio_policy_gap_service import (
    PortfolioPolicyGapService,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
)


def create_gap_result():
    portfolio = CurrentPortfolio(
        name="Contribution Test",
        policy=PortfolioPolicy(
            core_target_weight=0.80,
            tactical_target_weight=0.10,
            cash_target_weight=0.10,
            monthly_contribution=2000.0,
        ),
        holdings=(
            PortfolioHolding(
                symbol="WORLD",
                name="World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=70.0,
                average_cost=100.0,
                isin="IE00B4L5Y983",
                exchange_ticker="EUNL",
            ),
            PortfolioHolding(
                symbol="MSFT",
                name="Microsoft",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=1.0,
                average_cost=500.0,
                exchange_ticker="MSFT",
            ),
        ),
        cash_balance=2500.0,
    )

    snapshot = PortfolioSnapshotService().build(
        portfolio
    )

    return PortfolioPolicyGapService().calculate(
        snapshot=snapshot,
        policy=portfolio.policy,
    )


def test_planner_allocates_to_positive_gaps() -> None:
    plan = ContributionPlanner().plan(
        policy_gap=create_gap_result(),
        available_capital=2000.0,
    )

    assert plan.status == "ALLOCATE"
    assert plan.deployable_capital == 1500.0
    assert plan.retained_cash == 500.0
    assert [
        item.key
        for item in plan.items
    ] == [
        "CORE_LONG_TERM",
        "TACTICAL_TOTAL",
    ]


def test_planner_allocates_proportionally() -> None:
    plan = ContributionPlanner().plan(
        policy_gap=create_gap_result(),
        available_capital=1000.0,
    )

    amounts = {
        item.key: item.amount
        for item in plan.items
    }

    assert amounts["CORE_LONG_TERM"] == 666.67
    assert amounts["TACTICAL_TOTAL"] == 333.33


def test_planner_retains_excess_capital() -> None:
    plan = ContributionPlanner().plan(
        policy_gap=create_gap_result(),
        available_capital=5000.0,
    )

    assert plan.deployable_capital == 1500.0
    assert plan.retained_cash == 3500.0


def test_planner_handles_zero_capital() -> None:
    plan = ContributionPlanner().plan(
        policy_gap=create_gap_result(),
        available_capital=0.0,
    )

    assert plan.status == "NO_CAPITAL"
    assert plan.items == ()


def test_plan_is_json_ready() -> None:
    payload = ContributionPlanner().plan(
        policy_gap=create_gap_result(),
        available_capital=1000.0,
    ).to_dict()

    assert payload["status"] == "ALLOCATE"
    assert payload["available_capital"] == 1000.0
    assert payload["deployable_capital"] == 1000.0
    assert payload["items"][0]["key"] == (
        "CORE_LONG_TERM"
    )