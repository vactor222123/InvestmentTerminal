"""
Tests for long-term and position-trading holding strategies.
"""

import pytest

from investment_terminal.portfolio.current_portfolio_models import (
    PortfolioHolding,
)


def test_core_holding_defaults_to_core_long_term() -> None:
    holding = PortfolioHolding(
        symbol="WORLD",
        name="World ETF",
        asset_type="ETF",
        sleeve="CORE",
        quantity=10.0,
        average_cost=100.0,
        isin="IE00B4L5Y983",
        exchange_ticker="EUNL",
    )

    assert holding.strategy == "CORE_LONG_TERM"
    assert holding.to_dict()["strategy"] == (
        "CORE_LONG_TERM"
    )


def test_tactical_stock_defaults_to_stock_long_term() -> None:
    holding = PortfolioHolding(
        symbol="MSFT",
        name="Microsoft",
        asset_type="STOCK",
        sleeve="TACTICAL",
        quantity=1.0,
        average_cost=400.0,
        exchange_ticker="MSFT",
    )

    assert holding.strategy == "STOCK_LONG_TERM"


def test_position_trade_can_be_marked_explicitly() -> None:
    holding = PortfolioHolding(
        symbol="TSLA",
        name="Tesla",
        asset_type="STOCK",
        sleeve="TACTICAL",
        quantity=2.0,
        average_cost=250.0,
        exchange_ticker="TSLA",
        strategy="POSITION_TRADE",
    )

    assert holding.strategy == "POSITION_TRADE"


def test_position_trade_rejects_etf() -> None:
    with pytest.raises(
        ValueError,
        match="Stock strategies",
    ):
        PortfolioHolding(
            symbol="WORLD",
            name="World ETF",
            asset_type="ETF",
            sleeve="CORE",
            quantity=10.0,
            average_cost=100.0,
            isin="IE00B4L5Y983",
            exchange_ticker="EUNL",
            strategy="POSITION_TRADE",
        )


def test_core_long_term_rejects_tactical_sleeve() -> None:
    with pytest.raises(
        ValueError,
        match="CORE_LONG_TERM",
    ):
        PortfolioHolding(
            symbol="MSFT",
            name="Microsoft",
            asset_type="STOCK",
            sleeve="TACTICAL",
            quantity=1.0,
            average_cost=400.0,
            exchange_ticker="MSFT",
            strategy="CORE_LONG_TERM",
        )


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="strategy must be one of",
    ):
        PortfolioHolding(
            symbol="MSFT",
            name="Microsoft",
            asset_type="STOCK",
            sleeve="TACTICAL",
            quantity=1.0,
            average_cost=400.0,
            exchange_ticker="MSFT",
            strategy="SWING",
        )