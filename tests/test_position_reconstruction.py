"""Tests for deterministic position reconstruction."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.position_reconstruction import (
    PositionReconstructor,
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
EM = InstrumentIdentity(
    symbol="EM",
    name="Emerging Markets ETF",
    instrument_type="ETF",
    currency="EUR",
    isin="IE00BKM4GZ66",
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


def test_reconstructs_weighted_average_cost_after_buys() -> None:
    result = PositionReconstructor.reconstruct(
        ledger(
            trade("buy-1", "BUY", 1, 2, 100),
            trade("buy-2", "BUY", 2, 1, 130),
        )
    )

    assert result.processed_trade_count == 2
    assert len(result.positions) == 1
    assert result.positions[0].quantity == 3.0
    assert result.positions[0].cost_basis == 330.0
    assert result.positions[0].average_cost == 110.0


def test_sell_reduces_average_cost_basis_without_using_sale_price() -> None:
    result = PositionReconstructor.reconstruct(
        ledger(
            trade("buy-1", "BUY", 1, 3, 110),
            trade("sell-1", "SELL", 2, 1, 150),
        )
    )

    position = result.positions[0]
    assert position.quantity == 2.0
    assert position.cost_basis == 220.0
    assert position.average_cost == 110.0


def test_fully_sold_position_is_not_open() -> None:
    result = PositionReconstructor.reconstruct(
        ledger(
            trade("buy-1", "BUY", 1, 2, 100),
            trade("sell-1", "SELL", 2, 2, 90),
        )
    )

    assert result.positions == ()
    assert result.to_dict()["position_count"] == 0


def test_non_trade_events_are_ignored() -> None:
    dividend = PortfolioTransaction(
        transaction_id="div-1",
        transaction_type="DIVIDEND",
        occurred_at=datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
        settlement_currency="EUR",
        instrument=WORLD,
        cash_amount=5,
    )
    result = PositionReconstructor.reconstruct(
        ledger(trade("buy-1", "BUY", 1, 1, 100), dividend)
    )

    assert result.processed_trade_count == 1
    assert result.positions[0].quantity == 1.0


def test_positions_are_ordered_by_instrument_key() -> None:
    result = PositionReconstructor.reconstruct(
        ledger(
            trade("world", "BUY", 1, 1, 100),
            trade("em", "BUY", 2, 2, 50, instrument=EM),
        )
    )

    assert tuple(item.instrument_key for item in result.positions) == tuple(
        sorted((WORLD.instrument_key, EM.instrument_key))
    )


def test_sell_cannot_exceed_available_quantity() -> None:
    with pytest.raises(ValueError, match="sell-1 exceeds available quantity"):
        PositionReconstructor.reconstruct(
            ledger(
                trade("buy-1", "BUY", 1, 1, 100),
                trade("sell-1", "SELL", 2, 2, 120),
            )
        )


def test_sell_before_buy_fails_closed() -> None:
    with pytest.raises(ValueError, match="sell-1 exceeds available quantity"):
        PositionReconstructor.reconstruct(ledger(trade("sell-1", "SELL", 1, 1, 120)))


def test_instrument_identity_cannot_change_for_same_key() -> None:
    renamed = InstrumentIdentity(
        symbol="WORLD",
        name="Renamed World ETF",
        instrument_type="ETF",
        currency="EUR",
        isin=WORLD.isin,
    )
    with pytest.raises(ValueError, match="instrument identity changed"):
        PositionReconstructor.reconstruct(
            ledger(
                trade("buy-1", "BUY", 1, 1, 100),
                trade("buy-2", "BUY", 2, 1, 100, instrument=renamed),
            )
        )


def test_instrument_identity_cannot_change_after_position_was_closed() -> None:
    renamed = InstrumentIdentity(
        symbol="WORLD",
        name="Renamed World ETF",
        instrument_type="ETF",
        currency="EUR",
        isin=WORLD.isin,
    )
    with pytest.raises(ValueError, match="instrument identity changed"):
        PositionReconstructor.reconstruct(
            ledger(
                trade("buy-1", "BUY", 1, 1, 100),
                trade("sell-1", "SELL", 2, 1, 110),
                trade("buy-2", "BUY", 3, 1, 120, instrument=renamed),
            )
        )


def test_cost_currency_cannot_change_for_open_position() -> None:
    with pytest.raises(ValueError, match="settlement currency changed"):
        PositionReconstructor.reconstruct(
            ledger(
                trade("buy-1", "BUY", 1, 1, 100),
                trade("buy-2", "BUY", 2, 1, 100, currency="USD"),
            )
        )
