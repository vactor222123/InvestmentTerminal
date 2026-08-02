"""
Tests for portfolio strategy breakdown in snapshots.
"""

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
)


def create_strategy_portfolio() -> CurrentPortfolio:
    return CurrentPortfolio(
        name="Strategy Portfolio",
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
                quantity=100.0,
                average_cost=100.0,
                isin="IE00B4L5Y983",
                exchange_ticker="EUNL",
            ),
            PortfolioHolding(
                symbol="MSFT",
                name="Microsoft",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=2.0,
                average_cost=500.0,
                exchange_ticker="MSFT",
                strategy="STOCK_LONG_TERM",
            ),
            PortfolioHolding(
                symbol="TSLA",
                name="Tesla",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=2.0,
                average_cost=250.0,
                exchange_ticker="TSLA",
                strategy="POSITION_TRADE",
            ),
        ),
        cash_balance=1500.0,
    )


def test_snapshot_calculates_strategy_breakdown() -> None:
    snapshot = PortfolioSnapshotService().build(
        create_strategy_portfolio()
    )

    assert snapshot.total_value == 13000.0
    assert snapshot.strategy(
        "CORE_LONG_TERM"
    ).amount == 10000.0
    assert snapshot.strategy(
        "STOCK_LONG_TERM"
    ).amount == 1000.0
    assert snapshot.strategy(
        "POSITION_TRADE"
    ).amount == 500.0
    assert snapshot.strategy(
        "CASH_RESERVE"
    ).amount == 1500.0


def test_strategy_breakdown_weights_use_total_portfolio() -> None:
    snapshot = PortfolioSnapshotService().build(
        create_strategy_portfolio()
    )

    assert snapshot.strategy(
        "CORE_LONG_TERM"
    ).weight == round(
        10000.0 / 13000.0,
        8,
    )
    assert snapshot.strategy(
        "CASH_RESERVE"
    ).weight == round(
        1500.0 / 13000.0,
        8,
    )


def test_strategy_breakdown_is_exported() -> None:
    payload = PortfolioSnapshotService().build(
        create_strategy_portfolio()
    ).to_dict()

    strategies = {
        item["key"]: item
        for item in payload["strategy_breakdown"]
    }

    assert strategies[
        "POSITION_TRADE"
    ]["amount"] == 500.0
    assert strategies[
        "CASH_RESERVE"
    ]["amount"] == 1500.0


def test_empty_portfolio_has_zero_strategy_weights() -> None:
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

    assert all(
        item.amount == 0.0
        and item.weight == 0.0
        for item in snapshot.strategy_breakdown
    )