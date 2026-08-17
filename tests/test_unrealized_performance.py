"""Tests for transaction-derived unrealised performance."""

from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.portfolio_market_value_models import (
    PortfolioPriceQuote,
)
from investment_terminal.portfolio.portfolio_price_provider import (
    InMemoryPortfolioPriceProvider,
)
from investment_terminal.portfolio.position_reconstruction import (
    PositionReconstruction,
    ReconstructedPosition,
)
from investment_terminal.portfolio.unrealized_performance import (
    UnrealizedPerformanceCalculator,
)

VALUED_AT = datetime(2026, 8, 17, 18, tzinfo=timezone.utc)
WORLD = InstrumentIdentity(
    symbol="WORLD",
    name="World ETF",
    instrument_type="ETF",
    currency="EUR",
    isin="IE00B4L5Y983",
    exchange_ticker="IWDA",
)
STOCK = InstrumentIdentity(
    symbol="MSFT",
    name="Microsoft",
    instrument_type="STOCK",
    currency="USD",
    exchange_ticker="MSFT",
)


def position(
    instrument: InstrumentIdentity = WORLD,
    *,
    quantity: float = 2,
    cost_basis: float = 200,
    average_cost: float = 100,
    currency: str = "EUR",
) -> ReconstructedPosition:
    return ReconstructedPosition(
        instrument=instrument,
        quantity=quantity,
        cost_basis=cost_basis,
        average_cost=average_cost,
        cost_currency=currency,
    )


def reconstruction(*positions: ReconstructedPosition) -> PositionReconstruction:
    return PositionReconstruction(
        ledger_id="main",
        portfolio_name="Personal",
        processed_trade_count=2,
        positions=tuple(sorted(positions, key=lambda item: item.instrument_key)),
    )


def quote(
    instrument: InstrumentIdentity = WORLD,
    *,
    price: float = 125,
    currency: str = "EUR",
    quoted_at: datetime = VALUED_AT,
) -> PortfolioPriceQuote:
    assert instrument.exchange_ticker is not None
    return PortfolioPriceQuote(
        instrument_key=instrument.instrument_key,
        exchange_ticker=instrument.exchange_ticker,
        price=price,
        currency=currency,
        quoted_at=quoted_at,
        source="TEST",
    )


def calculator(*quotes: PortfolioPriceQuote) -> UnrealizedPerformanceCalculator:
    return UnrealizedPerformanceCalculator(
        InMemoryPortfolioPriceProvider({item.instrument_key: item for item in quotes})
    )


def test_calculates_position_unrealised_performance_with_provenance() -> None:
    result = calculator(quote()).calculate(
        reconstruction(position()),
        valued_at=VALUED_AT,
    )

    valued = result.positions[0]
    assert valued.market_value == 250.0
    assert valued.unrealized_gain_loss == 50.0
    assert valued.unrealized_return_percent == 25.0
    assert valued.quoted_at == VALUED_AT
    assert valued.quote_source == "TEST"


def test_currency_summaries_remain_separate_and_ordered() -> None:
    result = calculator(
        quote(),
        quote(STOCK, price=180, currency="USD"),
    ).calculate(
        reconstruction(
            position(),
            position(
                STOCK, quantity=1, cost_basis=200, average_cost=200, currency="USD"
            ),
        ),
        valued_at=VALUED_AT,
    )

    assert tuple(item.currency for item in result.currency_summaries) == (
        "EUR",
        "USD",
    )
    assert result.currency_summaries[0].unrealized_gain_loss == 50.0
    assert result.currency_summaries[1].unrealized_gain_loss == -20.0


def test_zero_cost_basis_has_explicit_missing_return_percent() -> None:
    result = calculator(quote(price=10)).calculate(
        reconstruction(position(quantity=1, cost_basis=0, average_cost=0)),
        valued_at=VALUED_AT,
    )

    assert result.positions[0].unrealized_return_percent is None
    assert result.currency_summaries[0].unrealized_return_percent is None


def test_missing_exchange_ticker_fails_closed() -> None:
    no_ticker = InstrumentIdentity(
        symbol="WORLD",
        name="World ETF",
        instrument_type="ETF",
        currency="EUR",
        isin="IE00B4L5Y983",
    )
    with pytest.raises(ValueError, match="has no exchange_ticker"):
        calculator().calculate(
            reconstruction(position(no_ticker)),
            valued_at=VALUED_AT,
        )


def test_missing_quote_remains_visible() -> None:
    with pytest.raises(KeyError, match="No portfolio price quote"):
        calculator().calculate(
            reconstruction(position()),
            valued_at=VALUED_AT,
        )


def test_quote_currency_must_match_cost_currency() -> None:
    with pytest.raises(ValueError, match="cost currency and quote currency"):
        calculator(quote(currency="USD")).calculate(
            reconstruction(position()),
            valued_at=VALUED_AT,
        )


def test_future_quote_fails_closed() -> None:
    with pytest.raises(ValueError, match="must not be later"):
        calculator(quote(quoted_at=VALUED_AT + timedelta(seconds=1))).calculate(
            reconstruction(position()),
            valued_at=VALUED_AT,
        )


def test_empty_reconstruction_produces_empty_projection() -> None:
    result = calculator().calculate(
        reconstruction(),
        valued_at=VALUED_AT,
    )

    assert result.positions == ()
    assert result.currency_summaries == ()
    assert result.to_dict()["position_count"] == 0
