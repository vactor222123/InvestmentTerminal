"""Tests for deterministic realised performance calculation."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.realized_performance import (
    RealizedPerformanceCalculator,
)
from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
    PortfolioTransactionLedger,
)

WORLD = InstrumentIdentity(
    symbol="WORLD",
    name="World ETF",
    instrument_type="ETF",
    currency="EUR",
    isin="IE00B4L5Y983",
)
STOCK = InstrumentIdentity(
    symbol="MSFT",
    name="Microsoft",
    instrument_type="STOCK",
    currency="USD",
    exchange_ticker="MSFT",
)


def trade(
    transaction_id: str,
    transaction_type: str,
    day: int,
    quantity: float,
    unit_price: float,
    *,
    instrument: InstrumentIdentity = WORLD,
    currency: str = "EUR",
) -> PortfolioTransaction:
    return PortfolioTransaction(
        transaction_id=transaction_id,
        transaction_type=transaction_type,
        occurred_at=datetime(2026, 8, day, 12, tzinfo=timezone.utc),
        settlement_currency=currency,
        instrument=instrument,
        quantity=quantity,
        unit_price=unit_price,
    )


def ledger(*transactions: PortfolioTransaction) -> PortfolioTransactionLedger:
    return PortfolioTransactionLedger(
        ledger_id="main",
        portfolio_name="Personal",
        base_currency="EUR",
        transactions=transactions,
    )


def test_calculates_gain_from_one_sale() -> None:
    result = RealizedPerformanceCalculator.calculate(
        ledger(
            trade("buy-1", "BUY", 1, 2, 100),
            trade("sell-1", "SELL", 2, 1, 130),
        )
    )

    sale = result.sales[0]
    assert sale.sell_transaction_id == "sell-1"
    assert sale.proceeds == 130.0
    assert sale.allocated_cost_basis == 100.0
    assert sale.realized_gain_loss == 30.0
    assert sale.realized_return_percent == 30.0


def test_uses_weighted_average_cost_and_preserves_loss() -> None:
    result = RealizedPerformanceCalculator.calculate(
        ledger(
            trade("buy-1", "BUY", 1, 2, 100),
            trade("buy-2", "BUY", 2, 1, 130),
            trade("sell-1", "SELL", 3, 1.5, 90),
        )
    )

    sale = result.sales[0]
    assert sale.allocated_cost_basis == 165.0
    assert sale.proceeds == 135.0
    assert sale.realized_gain_loss == -30.0
    assert sale.realized_return_percent == pytest.approx(-18.1818181818)


def test_zero_cost_basis_has_explicit_missing_return_percent() -> None:
    result = RealizedPerformanceCalculator.calculate(
        ledger(
            trade("buy-1", "BUY", 1, 1, 0),
            trade("sell-1", "SELL", 2, 1, 10),
        )
    )

    assert result.sales[0].realized_gain_loss == 10.0
    assert result.sales[0].realized_return_percent is None


def test_summaries_do_not_mix_currencies() -> None:
    result = RealizedPerformanceCalculator.calculate(
        ledger(
            trade("eur-buy", "BUY", 1, 1, 100),
            trade("usd-buy", "BUY", 2, 1, 200, instrument=STOCK, currency="USD"),
            trade("eur-sell", "SELL", 3, 1, 110),
            trade(
                "usd-sell",
                "SELL",
                4,
                1,
                180,
                instrument=STOCK,
                currency="USD",
            ),
        )
    )

    assert tuple(item.currency for item in result.currency_summaries) == (
        "EUR",
        "USD",
    )
    assert result.currency_summaries[0].realized_gain_loss == 10.0
    assert result.currency_summaries[1].realized_gain_loss == -20.0


def test_non_trade_events_do_not_create_sales() -> None:
    dividend = PortfolioTransaction(
        transaction_id="div-1",
        transaction_type="DIVIDEND",
        occurred_at=datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
        settlement_currency="EUR",
        instrument=WORLD,
        cash_amount=5,
    )

    result = RealizedPerformanceCalculator.calculate(ledger(dividend))

    assert result.sales == ()
    assert result.currency_summaries == ()
    assert result.to_dict()["sale_count"] == 0


def test_sell_cannot_exceed_available_quantity() -> None:
    with pytest.raises(ValueError, match="sell-1 exceeds available quantity"):
        RealizedPerformanceCalculator.calculate(
            ledger(
                trade("buy-1", "BUY", 1, 1, 100),
                trade("sell-1", "SELL", 2, 2, 120),
            )
        )


def test_identity_drift_fails_closed_after_position_is_closed() -> None:
    renamed = InstrumentIdentity(
        symbol="WORLD",
        name="Renamed World ETF",
        instrument_type="ETF",
        currency="EUR",
        isin=WORLD.isin,
    )
    with pytest.raises(ValueError, match="instrument identity changed"):
        RealizedPerformanceCalculator.calculate(
            ledger(
                trade("buy-1", "BUY", 1, 1, 100),
                trade("sell-1", "SELL", 2, 1, 110),
                trade("buy-2", "BUY", 3, 1, 120, instrument=renamed),
            )
        )


def test_mixed_currency_for_open_position_fails_closed() -> None:
    with pytest.raises(ValueError, match="settlement currency changed"):
        RealizedPerformanceCalculator.calculate(
            ledger(
                trade("buy-1", "BUY", 1, 1, 100),
                trade("sell-1", "SELL", 2, 1, 120, currency="USD"),
            )
        )
