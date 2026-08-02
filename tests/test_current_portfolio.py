"""
Tests for current portfolio models and JSON loader.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)


def create_policy() -> PortfolioPolicy:
    return PortfolioPolicy(
        core_target_weight=0.85,
        tactical_target_weight=0.10,
        cash_target_weight=0.05,
        monthly_contribution=2000.0,
        base_currency="EUR",
    )


def test_policy_matches_core_tactical_goal() -> None:
    policy = create_policy()

    assert policy.core_target_weight == 0.85
    assert policy.tactical_target_weight == 0.10
    assert policy.cash_target_weight == 0.05
    assert policy.invested_target_weight == 0.95


def test_policy_rejects_invalid_total() -> None:
    with pytest.raises(
        ValueError,
        match="sum to 1.0",
    ):
        PortfolioPolicy(
            core_target_weight=0.85,
            tactical_target_weight=0.10,
            cash_target_weight=0.10,
            monthly_contribution=2000.0,
        )


def test_policy_rejects_core_outside_goal_range() -> None:
    with pytest.raises(
        ValueError,
        match="core_target_weight",
    ):
        PortfolioPolicy(
            core_target_weight=0.80,
            tactical_target_weight=0.15,
            cash_target_weight=0.05,
            monthly_contribution=2000.0,
        )


def test_holding_calculates_invested_cost() -> None:
    holding = PortfolioHolding(
        symbol="IWDA",
        name="MSCI World ETF",
        asset_type="ETF",
        sleeve="CORE",
        quantity=10.0,
        average_cost=100.0,
        currency="EUR",
        isin="IE00B4L5Y983",
        exchange_ticker="IWDA",
    )

    assert holding.invested_cost == 1000.0


def test_individual_stock_must_be_tactical() -> None:
    with pytest.raises(
        ValueError,
        match="TACTICAL",
    ):
        PortfolioHolding(
            symbol="MSFT",
            name="Microsoft",
            asset_type="STOCK",
            sleeve="CORE",
            quantity=1.0,
            average_cost=400.0,
        )


def test_portfolio_calculates_sleeve_totals() -> None:
    portfolio = CurrentPortfolio(
        name="Test Portfolio",
        policy=create_policy(),
        holdings=(
            PortfolioHolding(
                symbol="IWDA",
                name="MSCI World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=10.0,
                average_cost=100.0,
                isin="IE00B4L5Y983",
                exchange_ticker="IWDA",
            ),
            PortfolioHolding(
                symbol="MSFT",
                name="Microsoft",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=2.0,
                average_cost=400.0,
            ),
        ),
        cash_balance=1600.0,
    )

    assert portfolio.core_cost == 1000.0
    assert portfolio.tactical_cost == 800.0
    assert portfolio.invested_cost == 1800.0
    assert portfolio.total_cost_basis == 3400.0


def test_portfolio_rejects_duplicate_instruments() -> None:
    holding = PortfolioHolding(
        symbol="IWDA",
        name="MSCI World ETF",
        asset_type="ETF",
        sleeve="CORE",
        quantity=10.0,
        average_cost=100.0,
        isin="IE00B4L5Y983",
        exchange_ticker="IWDA",
    )

    with pytest.raises(
        ValueError,
        match="unique instruments",
    ):
        CurrentPortfolio(
            name="Test",
            policy=create_policy(),
            holdings=(
                holding,
                holding,
            ),
            cash_balance=0.0,
        )


def test_loader_reads_example_template() -> None:
    portfolio = CurrentPortfolioLoader.load(
        Path(
            "data/portfolios/current_portfolio.example.json"
        )
    )

    assert portfolio.name == (
        "Example Investment Portfolio"
    )
    assert portfolio.cash_balance == 1000.0
    assert portfolio.policy.monthly_contribution == 2000.0
    assert len(portfolio.holdings) == 2


def test_loader_reads_holdings(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "portfolio.json"
    )
    path.write_text(
        json.dumps(
            {
                "name": "Test",
                "policy": {
                    "core_target_weight": 0.85,
                    "tactical_target_weight": 0.10,
                    "cash_target_weight": 0.05,
                    "monthly_contribution": 2000.0,
                    "base_currency": "EUR"
                },
                "cash_balance": 500.0,
                "holdings": [
                    {
                        "symbol": "IWDA",
                        "name": "MSCI World ETF",
                        "asset_type": "ETF",
                        "sleeve": "CORE",
                        "quantity": 2.0,
                        "average_cost": 100.0,
                        "isin": "IE00B4L5Y983",
                        "exchange_ticker": "IWDA"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    portfolio = CurrentPortfolioLoader.load(
        path
    )

    assert len(portfolio.holdings) == 1
    assert portfolio.holdings[0].symbol == "IWDA"
    assert portfolio.total_cost_basis == 700.0


def test_loader_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "invalid.json"
    )
    path.write_text(
        "{invalid",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="invalid JSON",
    ):
        CurrentPortfolioLoader.load(
            path
        )