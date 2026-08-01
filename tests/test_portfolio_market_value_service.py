"""
Tests for portfolio market-value calculation.
"""

from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)
from investment_terminal.portfolio.portfolio_market_value_models import (
    PortfolioMarketPosition,
    PortfolioPriceQuote,
)
from investment_terminal.portfolio.portfolio_market_value_service import (
    PortfolioMarketValueService,
)
from investment_terminal.portfolio.portfolio_price_provider import (
    InMemoryPortfolioPriceProvider,
)


QUOTED_AT = datetime(
    2026,
    8,
    1,
    18,
    0,
    tzinfo=timezone.utc,
)


def create_portfolio() -> CurrentPortfolio:
    return CurrentPortfolio(
        name="Test Portfolio",
        policy=PortfolioPolicy(
            core_target_weight=0.85,
            tactical_target_weight=0.10,
            cash_target_weight=0.05,
            monthly_contribution=2000.0,
            base_currency="EUR",
        ),
        holdings=(
            PortfolioHolding(
                symbol="WORLD",
                name="World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=10.5,
                average_cost=100.25,
                currency="EUR",
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
                currency="EUR",
                exchange_ticker="MSFT",
            ),
        ),
        cash_balance=1600.0,
    )


def create_provider() -> InMemoryPortfolioPriceProvider:
    return InMemoryPortfolioPriceProvider(
        {
            "IE00B4L5Y983": PortfolioPriceQuote(
                instrument_key="IE00B4L5Y983",
                exchange_ticker="IWDA",
                price=110.0,
                currency="EUR",
                quoted_at=QUOTED_AT,
                source="TEST",
            ),
            "MSFT": PortfolioPriceQuote(
                instrument_key="MSFT",
                exchange_ticker="MSFT",
                price=450.0,
                currency="EUR",
                quoted_at=QUOTED_AT,
                source="TEST",
            ),
        }
    )


def test_position_calculates_market_value_and_profit() -> None:
    holding = create_portfolio().holdings[0]
    quote = create_provider().get_quote(
        instrument_key=holding.instrument_key,
        exchange_ticker=holding.exchange_ticker,
    )

    position = PortfolioMarketPosition.build(
        holding,
        quote,
    )

    assert position.cost_basis == 1052.63
    assert position.market_value == 1155.0
    assert position.unrealized_profit_loss == 102.37
    assert position.unrealized_return_percent == pytest.approx(
        9.7252,
        abs=0.0001,
    )


def test_service_calculates_portfolio_market_value() -> None:
    result = PortfolioMarketValueService(
        create_provider()
    ).calculate(
        create_portfolio(),
        generated_at=QUOTED_AT,
    )

    assert result.invested_cost_basis == 1852.63
    assert result.invested_market_value == 2055.0
    assert result.cash_value == 1600.0
    assert result.total_market_value == 3655.0
    assert result.unrealized_profit_loss == 202.37
    assert result.unrealized_return_percent == pytest.approx(
    10.9234,
    abs=0.0001,
)


def test_service_rejects_holding_without_ticker() -> None:
    portfolio = CurrentPortfolio(
        name="Missing ticker",
        policy=create_portfolio().policy,
        holdings=(
            PortfolioHolding(
                symbol="WORLD",
                name="World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=1.0,
                average_cost=100.0,
                currency="EUR",
                isin="IE00B4L5Y983",
            ),
        ),
        cash_balance=0.0,
    )

    with pytest.raises(
        ValueError,
        match="exchange_ticker",
    ):
        PortfolioMarketValueService(
            create_provider()
        ).calculate(
            portfolio
        )


def test_position_rejects_currency_mismatch() -> None:
    holding = create_portfolio().holdings[0]
    quote = PortfolioPriceQuote(
        instrument_key=holding.instrument_key,
        exchange_ticker="IWDA",
        price=110.0,
        currency="USD",
        quoted_at=QUOTED_AT,
        source="TEST",
    )

    with pytest.raises(
        ValueError,
        match="currencies must match",
    ):
        PortfolioMarketPosition.build(
            holding,
            quote,
        )


def test_provider_reports_missing_quote() -> None:
    with pytest.raises(
        KeyError,
        match="No portfolio price quote",
    ):
        create_provider().get_quote(
            instrument_key="UNKNOWN",
            exchange_ticker="UNKNOWN",
        )


def test_empty_portfolio_keeps_cash_value() -> None:
    portfolio = CurrentPortfolio(
        name="Cash only",
        policy=create_portfolio().policy,
        holdings=(),
        cash_balance=1600.0,
    )

    result = PortfolioMarketValueService(
        InMemoryPortfolioPriceProvider(
            {}
        )
    ).calculate(
        portfolio,
        generated_at=QUOTED_AT,
    )

    assert result.positions == ()
    assert result.invested_market_value == 0.0
    assert result.total_market_value == 1600.0
    assert result.unrealized_return == 0.0