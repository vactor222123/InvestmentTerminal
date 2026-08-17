"""Tests for explicit portfolio tax-lot attribution."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.tax_lot_attribution import (
    TaxLotAttributor,
    TaxLotSelection,
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
OTHER = InstrumentIdentity(
    symbol="OTHER",
    name="Other ETF",
    instrument_type="ETF",
    currency="EUR",
    isin="IE00BKM4GZ66",
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


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
        occurred_at=ts(day),
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
        transactions=tuple(transactions),
    )


def test_explicit_selection_preserves_lot_cost_and_sale_proceeds() -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 2, 100),
        trade("buy-2", "BUY", 2, 3, 120),
        trade("sell-1", "SELL", 3, 2.5, 150),
    )

    result = TaxLotAttributor.attribute(
        source,
        (
            TaxLotSelection("sell-1", "buy-2", 2),
            TaxLotSelection("sell-1", "buy-1", 0.5),
        ),
    )

    assert tuple(item.acquisition_transaction_id for item in result.allocations) == (
        "buy-1",
        "buy-2",
    )
    assert result.allocations[0].allocated_cost_basis == 50
    assert result.allocations[0].proceeds == 75
    assert result.allocations[0].realized_gain_loss == 25
    assert tuple(item.remaining_quantity for item in result.open_lots) == (1.5, 1.0)
    assert result.open_lots[0].remaining_cost_basis == 150
    assert result.to_dict()["allocation_count"] == 2


def test_output_is_deterministic_independent_of_selection_order() -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 2, 100),
        trade("buy-2", "BUY", 2, 2, 120),
        trade("sell-1", "SELL", 3, 2, 150),
    )
    first = TaxLotSelection("sell-1", "buy-1", 1)
    second = TaxLotSelection("sell-1", "buy-2", 1)

    assert TaxLotAttributor.attribute(source, (first, second)) == (
        TaxLotAttributor.attribute(source, (second, first))
    )


def test_fully_consumed_lot_is_not_reported_as_open() -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 2, 100),
        trade("sell-1", "SELL", 2, 2, 150),
    )
    result = TaxLotAttributor.attribute(
        source, (TaxLotSelection("sell-1", "buy-1", 2),)
    )
    assert result.open_lots == ()


def test_cash_events_are_ignored() -> None:
    dividend = PortfolioTransaction(
        transaction_id="dividend-1",
        transaction_type="DIVIDEND",
        occurred_at=ts(2),
        settlement_currency="EUR",
        instrument=WORLD,
        cash_amount=10,
    )
    result = TaxLotAttributor.attribute(
        ledger(trade("buy-1", "BUY", 1, 2, 100), dividend), ()
    )
    assert result.processed_trade_count == 1
    assert result.open_lots[0].remaining_quantity == 2


@pytest.mark.parametrize("selected", [0.5, 1.5])
def test_every_sale_must_be_attributed_exactly(selected: float) -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 2, 100),
        trade("sell-1", "SELL", 2, 1, 150),
    )
    with pytest.raises(ValueError, match="must be attributed exactly"):
        TaxLotAttributor.attribute(
            source, (TaxLotSelection("sell-1", "buy-1", selected),)
        )


def test_acquisition_capacity_cannot_be_reused_across_sales() -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 1, 100),
        trade("sell-1", "SELL", 2, 0.6, 150),
        trade("sell-2", "SELL", 3, 0.6, 160),
    )
    with pytest.raises(ValueError, match="exceeds available quantity"):
        TaxLotAttributor.attribute(
            source,
            (
                TaxLotSelection("sell-1", "buy-1", 0.6),
                TaxLotSelection("sell-2", "buy-1", 0.6),
            ),
        )


def test_selection_references_existing_buy_and_sell_transactions() -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 1, 100),
        trade("sell-1", "SELL", 2, 1, 150),
    )
    with pytest.raises(ValueError, match="SELL transaction missing"):
        TaxLotAttributor.attribute(source, (TaxLotSelection("missing", "buy-1", 1),))
    with pytest.raises(ValueError, match="BUY transaction missing"):
        TaxLotAttributor.attribute(source, (TaxLotSelection("sell-1", "missing", 1),))


def test_acquisition_must_precede_matching_sale() -> None:
    source = ledger(
        trade("sell-1", "SELL", 1, 1, 150),
        trade("buy-1", "BUY", 2, 1, 100),
    )
    with pytest.raises(ValueError, match="must not be later"):
        TaxLotAttributor.attribute(source, (TaxLotSelection("sell-1", "buy-1", 1),))


@pytest.mark.parametrize(
    ("buy", "message"),
    [
        (trade("buy-1", "BUY", 1, 1, 100, instrument=OTHER), "same instrument"),
        (trade("buy-1", "BUY", 1, 1, 100, currency="USD"), "same currency"),
    ],
)
def test_selection_requires_compatible_trade_evidence(
    buy: PortfolioTransaction, message: str
) -> None:
    source = ledger(buy, trade("sell-1", "SELL", 2, 1, 150))
    with pytest.raises(ValueError, match=message):
        TaxLotAttributor.attribute(source, (TaxLotSelection("sell-1", "buy-1", 1),))


def test_duplicate_sale_acquisition_pair_is_rejected() -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 2, 100),
        trade("sell-1", "SELL", 2, 2, 150),
    )
    with pytest.raises(ValueError, match="unique sale/acquisition pairs"):
        TaxLotAttributor.attribute(
            source,
            (
                TaxLotSelection("sell-1", "buy-1", 1),
                TaxLotSelection("sell-1", "buy-1", 1),
            ),
        )


def test_no_implicit_lot_method_is_applied() -> None:
    source = ledger(
        trade("buy-1", "BUY", 1, 2, 100),
        trade("sell-1", "SELL", 2, 1, 150),
    )
    with pytest.raises(ValueError, match="must be attributed exactly"):
        TaxLotAttributor.attribute(source, ())
