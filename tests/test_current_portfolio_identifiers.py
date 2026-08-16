"""
Tests for instrument identifiers in the current portfolio.
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


def test_etf_requires_isin() -> None:
    with pytest.raises(
        ValueError,
        match="must provide an ISIN",
    ):
        PortfolioHolding(
            symbol="IWDA",
            name="MSCI World ETF",
            asset_type="ETF",
            sleeve="CORE",
            quantity=1.0,
            average_cost=100.0,
        )


def test_stock_can_use_exchange_ticker_without_isin() -> None:
    holding = PortfolioHolding(
        symbol="MSFT",
        name="Microsoft",
        asset_type="STOCK",
        sleeve="TACTICAL",
        quantity=1.0,
        average_cost=400.0,
        exchange_ticker="MSFT",
    )

    assert holding.isin is None
    assert holding.instrument_key == "MSFT"


def test_isin_is_normalized() -> None:
    holding = PortfolioHolding(
        symbol="world",
        name="World ETF",
        asset_type="ETF",
        sleeve="CORE",
        quantity=1.0,
        average_cost=100.0,
        isin=" ie00b4l5y983 ",
        exchange_ticker="iwda",
    )

    assert holding.symbol == "WORLD"
    assert holding.isin == "IE00B4L5Y983"
    assert holding.exchange_ticker == "IWDA"
    assert holding.instrument_key == "IE00B4L5Y983"
    assert holding.identity.to_dict() == {
        "symbol": "WORLD",
        "name": "World ETF",
        "instrument_type": "ETF",
        "currency": "EUR",
        "isin": "IE00B4L5Y983",
        "exchange_ticker": "IWDA",
        "exchange_code": None,
        "instrument_key": "IE00B4L5Y983",
    }


@pytest.mark.parametrize(
    "isin",
    [
        "IE123",
        "123456789012",
        "IE00B4L5Y98!",
    ],
)
def test_invalid_isin_is_rejected(
    isin: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="isin",
    ):
        PortfolioHolding(
            symbol="ETF",
            name="ETF",
            asset_type="ETF",
            sleeve="CORE",
            quantity=1.0,
            average_cost=100.0,
            isin=isin,
        )


def test_portfolio_rejects_duplicate_isin() -> None:
    first = PortfolioHolding(
        symbol="WORLD_A",
        name="World ETF",
        asset_type="ETF",
        sleeve="CORE",
        quantity=1.0,
        average_cost=100.0,
        isin="IE00B4L5Y983",
    )
    second = PortfolioHolding(
        symbol="WORLD_B",
        name="Same World ETF",
        asset_type="ETF",
        sleeve="CORE",
        quantity=2.0,
        average_cost=110.0,
        isin="IE00B4L5Y983",
    )

    with pytest.raises(
        ValueError,
        match="unique instruments",
    ):
        CurrentPortfolio(
            name="Test",
            policy=create_policy(),
            holdings=(
                first,
                second,
            ),
            cash_balance=0.0,
        )


def test_loader_reads_instrument_identifiers(
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
                        "symbol": "WORLD",
                        "name": "MSCI World ETF",
                        "asset_type": "ETF",
                        "sleeve": "CORE",
                        "quantity": 2.0,
                        "average_cost": 100.0,
                        "currency": "EUR",
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

    holding = portfolio.holdings[0]

    assert holding.isin == "IE00B4L5Y983"
    assert holding.exchange_ticker == "IWDA"
    assert holding.instrument_key == "IE00B4L5Y983"
