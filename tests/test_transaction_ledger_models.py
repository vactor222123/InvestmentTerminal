"""Tests for immutable portfolio transaction-ledger contracts."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
    PortfolioTransactionLedger,
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def instrument() -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol="WORLD",
        name="World ETF",
        instrument_type="ETF",
        currency="EUR",
        isin="IE00B4L5Y983",
    )


def buy(transaction_id: str = "tx-1", day: int = 1) -> PortfolioTransaction:
    return PortfolioTransaction(
        transaction_id=transaction_id,
        transaction_type="buy",
        occurred_at=timestamp(day),
        settlement_currency="eur",
        instrument=instrument(),
        quantity=2.5,
        unit_price=100.0,
        source_reference=" broker-1 ",
    )


def test_trade_normalizes_and_serializes_stably() -> None:
    data = buy().to_dict()

    assert data["transaction_type"] == "BUY"
    assert data["settlement_currency"] == "EUR"
    assert data["gross_amount"] == 250.0
    assert data["instrument"]["instrument_key"] == "IE00B4L5Y983"
    assert data["source_reference"] == "broker-1"


def test_dividend_requires_instrument_and_cash_amount() -> None:
    dividend = PortfolioTransaction(
        transaction_id="div-1",
        transaction_type="DIVIDEND",
        occurred_at=timestamp(2),
        settlement_currency="EUR",
        instrument=instrument(),
        cash_amount=12.5,
    )

    assert dividend.gross_amount == 12.5
    with pytest.raises(ValueError, match="require an instrument"):
        PortfolioTransaction(
            transaction_id="div-2",
            transaction_type="DIVIDEND",
            occurred_at=timestamp(2),
            settlement_currency="EUR",
            cash_amount=12.5,
        )


def test_fee_may_be_portfolio_level() -> None:
    fee = PortfolioTransaction(
        transaction_id="fee-1",
        transaction_type="FEE",
        occurred_at=timestamp(2),
        settlement_currency="EUR",
        cash_amount=1.25,
    )

    assert fee.instrument is None
    assert fee.gross_amount == 1.25


@pytest.mark.parametrize("transaction_type", ["BUY", "SELL"])
def test_trade_requires_instrument_quantity_and_price(
    transaction_type: str,
) -> None:
    with pytest.raises(ValueError, match="require an instrument"):
        PortfolioTransaction(
            transaction_id="trade-1",
            transaction_type=transaction_type,
            occurred_at=timestamp(1),
            settlement_currency="EUR",
            quantity=1.0,
            unit_price=10.0,
        )


def test_cash_event_rejects_trade_fields() -> None:
    with pytest.raises(ValueError, match="must not define quantity"):
        PortfolioTransaction(
            transaction_id="fee-1",
            transaction_type="FEE",
            occurred_at=timestamp(1),
            settlement_currency="EUR",
            quantity=1.0,
            cash_amount=2.0,
        )


def test_transaction_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        PortfolioTransaction(
            transaction_id="fee-1",
            transaction_type="FEE",
            occurred_at=datetime(2026, 8, 1, 12),
            settlement_currency="EUR",
            cash_amount=2.0,
        )


def test_ledger_serializes_deterministic_sequence() -> None:
    ledger = PortfolioTransactionLedger(
        ledger_id="main-ledger",
        portfolio_name="Personal",
        base_currency="eur",
        transactions=(buy("tx-1", 1), buy("tx-2", 2)),
    )

    data = ledger.to_dict()
    assert data["base_currency"] == "EUR"
    assert data["transaction_count"] == 2
    assert [item["transaction_id"] for item in data["transactions"]] == [
        "tx-1",
        "tx-2",
    ]


def test_ledger_rejects_duplicate_transaction_ids() -> None:
    with pytest.raises(ValueError, match="unique transaction IDs"):
        PortfolioTransactionLedger(
            ledger_id="main-ledger",
            portfolio_name="Personal",
            base_currency="EUR",
            transactions=(buy("tx-1", 1), buy("tx-1", 2)),
        )


def test_ledger_rejects_non_deterministic_order() -> None:
    with pytest.raises(ValueError, match="ordered"):
        PortfolioTransactionLedger(
            ledger_id="main-ledger",
            portfolio_name="Personal",
            base_currency="EUR",
            transactions=(buy("tx-2", 2), buy("tx-1", 1)),
        )
