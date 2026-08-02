"""
Tests for strategic portfolio policy gaps.
"""

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


def create_portfolio() -> CurrentPortfolio:
    return CurrentPortfolio(
        name="Gap Test",
        policy=PortfolioPolicy(
            core_target_weight=0.80,
            tactical_target_weight=0.10,
            cash_target_weight=0.10,
            monthly_contribution=2000.0,
            base_currency="EUR",
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
                strategy="STOCK_LONG_TERM",
            ),
            PortfolioHolding(
                symbol="TSLA",
                name="Tesla",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=1.0,
                average_cost=500.0,
                exchange_ticker="TSLA",
                strategy="POSITION_TRADE",
            ),
        ),
        cash_balance=2000.0,
    )


def test_gap_service_calculates_current_weights() -> None:
    portfolio = create_portfolio()
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )

    result = PortfolioPolicyGapService().calculate(
        snapshot=snapshot,
        policy=portfolio.policy,
    )

    assert result.total_value == 10000.0
    assert result.item(
        "CORE_LONG_TERM"
    ).current_weight == 0.70
    assert result.item(
        "TACTICAL_TOTAL"
    ).current_weight == 0.10
    assert result.item(
        "CASH_RESERVE"
    ).current_weight == 0.20


def test_gap_service_calculates_target_gaps() -> None:
    portfolio = create_portfolio()
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )

    result = PortfolioPolicyGapService().calculate(
        snapshot=snapshot,
        policy=portfolio.policy,
    )

    core = result.item(
        "CORE_LONG_TERM"
    )
    tactical = result.item(
        "TACTICAL_TOTAL"
    )
    cash = result.item(
        "CASH_RESERVE"
    )

    assert core.target_amount == 8000.0
    assert core.gap_amount == 1000.0
    assert core.status == "UNDERWEIGHT"

    assert tactical.gap_amount == 0.0
    assert tactical.status == "ON_TARGET"

    assert cash.gap_amount == -1000.0
    assert cash.status == "OVERWEIGHT"


def test_gap_result_is_json_ready() -> None:
    portfolio = create_portfolio()
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )

    payload = PortfolioPolicyGapService().calculate(
        snapshot=snapshot,
        policy=portfolio.policy,
    ).to_dict()

    assert payload["portfolio_name"] == "Gap Test"
    assert payload["items"][0]["key"] == (
        "CORE_LONG_TERM"
    )
    assert payload["items"][0]["gap_percent"] == 10.0
    assert payload["items"][2]["gap_percent"] == -10.0


def test_empty_portfolio_reports_policy_weights_as_gaps() -> None:
    portfolio = CurrentPortfolio(
        name="Empty",
        policy=PortfolioPolicy(
            core_target_weight=0.80,
            tactical_target_weight=0.10,
            cash_target_weight=0.10,
            monthly_contribution=2000.0,
        ),
        holdings=(),
        cash_balance=0.0,
    )
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )

    result = PortfolioPolicyGapService().calculate(
        snapshot=snapshot,
        policy=portfolio.policy,
    )

    assert result.item(
        "CORE_LONG_TERM"
    ).gap_weight == 0.80
    assert result.item(
        "TACTICAL_TOTAL"
    ).gap_weight == 0.10
    assert result.item(
        "CASH_RESERVE"
    ).gap_weight == 0.10