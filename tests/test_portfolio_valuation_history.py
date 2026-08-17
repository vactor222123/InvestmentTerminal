"""Tests for transaction-derived portfolio valuation-history contracts."""

from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.portfolio_valuation_history import (
    PortfolioValuationCurrencySnapshot,
    PortfolioValuationHistory,
    PortfolioValuationSnapshot,
)
from investment_terminal.portfolio.realized_performance import (
    RealizedCurrencySummary,
    RealizedPerformance,
    RealizedSale,
)
from investment_terminal.portfolio.unrealized_performance import (
    UnrealizedCurrencySummary,
    UnrealizedPerformance,
)
from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)

WORLD = InstrumentIdentity(
    symbol="WORLD",
    name="World ETF",
    instrument_type="ETF",
    currency="EUR",
    isin="IE00B4L5Y983",
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def unrealized(
    day: int = 2,
    *,
    ledger_id: str = "main",
    portfolio_name: str = "Personal",
) -> UnrealizedPerformance:
    return UnrealizedPerformance(
        ledger_id=ledger_id,
        portfolio_name=portfolio_name,
        valued_at=timestamp(day),
        positions=(),
        currency_summaries=(
            UnrealizedCurrencySummary(
                currency="EUR",
                cost_basis=200,
                market_value=250,
                unrealized_gain_loss=50,
                unrealized_return_percent=25,
            ),
        ),
    )


def realized(
    *,
    sale_day: int = 1,
    ledger_id: str = "main",
    portfolio_name: str = "Personal",
) -> RealizedPerformance:
    return RealizedPerformance(
        ledger_id=ledger_id,
        portfolio_name=portfolio_name,
        sales=(
            RealizedSale(
                sell_transaction_id="sell-1",
                occurred_at=timestamp(sale_day),
                instrument=WORLD,
                quantity=1,
                proceeds=130,
                allocated_cost_basis=100,
                realized_gain_loss=30,
                currency="EUR",
                realized_return_percent=30,
            ),
        ),
        currency_summaries=(
            RealizedCurrencySummary(
                currency="EUR",
                proceeds=130,
                allocated_cost_basis=100,
                realized_gain_loss=30,
            ),
        ),
    )


def snapshot(
    snapshot_id: str = "valuation-1",
    day: int = 2,
) -> PortfolioValuationSnapshot:
    return PortfolioValuationSnapshot.build(
        snapshot_id=snapshot_id,
        unrealized=unrealized(day),
        realized=realized(),
    )


def test_snapshot_combines_realized_and_unrealized_by_currency() -> None:
    result = snapshot()

    value = result.currency_values[0]
    assert value.open_cost_basis == 200
    assert value.market_value == 250
    assert value.unrealized_gain_loss == 50
    assert value.realized_gain_loss == 30
    assert value.combined_gain_loss == 80
    assert result.to_dict()["valued_at"] == timestamp(2).isoformat()


def test_snapshot_keeps_currency_rows_separate_and_ordered() -> None:
    realized_projection = RealizedPerformance(
        ledger_id="main",
        portfolio_name="Personal",
        sales=(),
        currency_summaries=(
            RealizedCurrencySummary(
                currency="USD",
                proceeds=120,
                allocated_cost_basis=100,
                realized_gain_loss=20,
            ),
        ),
    )

    result = PortfolioValuationSnapshot.build(
        snapshot_id="valuation-1",
        unrealized=unrealized(),
        realized=realized_projection,
    )

    assert tuple(item.currency for item in result.currency_values) == (
        "EUR",
        "USD",
    )
    assert result.currency_values[0].realized_gain_loss == 0
    assert result.currency_values[1].unrealized_gain_loss == 0


def test_snapshot_rejects_ledger_or_portfolio_mismatch() -> None:
    with pytest.raises(ValueError, match="same ledger_id"):
        PortfolioValuationSnapshot.build(
            snapshot_id="valuation-1",
            unrealized=unrealized(),
            realized=realized(ledger_id="other"),
        )
    with pytest.raises(ValueError, match="same portfolio_name"):
        PortfolioValuationSnapshot.build(
            snapshot_id="valuation-1",
            unrealized=unrealized(),
            realized=realized(portfolio_name="Other"),
        )


def test_snapshot_rejects_sale_after_valuation_time() -> None:
    with pytest.raises(ValueError, match="sales must not be later"):
        PortfolioValuationSnapshot.build(
            snapshot_id="valuation-1",
            unrealized=unrealized(day=2),
            realized=realized(sale_day=3),
        )


def test_snapshot_rejects_currency_values_not_derived_from_projections() -> None:
    with pytest.raises(ValueError, match="must match the performance projections"):
        PortfolioValuationSnapshot(
            snapshot_id="valuation-1",
            unrealized=unrealized(),
            realized=realized(),
            currency_values=(
                PortfolioValuationCurrencySnapshot(
                    currency="EUR",
                    open_cost_basis=200,
                    market_value=250,
                    unrealized_gain_loss=50,
                    realized_proceeds=130,
                    realized_cost_basis=100,
                    realized_gain_loss=30,
                    combined_gain_loss=80,
                ),
                PortfolioValuationCurrencySnapshot(
                    currency="USD",
                    open_cost_basis=0,
                    market_value=0,
                    unrealized_gain_loss=0,
                    realized_proceeds=0,
                    realized_cost_basis=0,
                    realized_gain_loss=0,
                    combined_gain_loss=0,
                ),
            ),
        )


def test_history_requires_deterministic_order() -> None:
    first = snapshot("valuation-1", day=2)
    second = snapshot("valuation-2", day=3)

    history = PortfolioValuationHistory(
        ledger_id="main",
        portfolio_name="Personal",
        snapshots=(first, second),
    )

    assert history.to_dict()["snapshot_count"] == 2
    with pytest.raises(ValueError, match="must be ordered"):
        PortfolioValuationHistory(
            ledger_id="main",
            portfolio_name="Personal",
            snapshots=(second, first),
        )


def test_history_rejects_duplicate_snapshot_identity() -> None:
    with pytest.raises(ValueError, match="unique snapshot IDs"):
        PortfolioValuationHistory(
            ledger_id="main",
            portfolio_name="Personal",
            snapshots=(snapshot(), snapshot()),
        )


def test_history_rejects_foreign_ledger_or_portfolio() -> None:
    foreign_ledger = PortfolioValuationSnapshot.build(
        snapshot_id="foreign-ledger",
        unrealized=unrealized(ledger_id="other"),
        realized=realized(ledger_id="other"),
    )
    foreign_portfolio = PortfolioValuationSnapshot.build(
        snapshot_id="foreign-portfolio",
        unrealized=unrealized(portfolio_name="Other"),
        realized=realized(portfolio_name="Other"),
    )
    with pytest.raises(ValueError, match="history ledger_id"):
        PortfolioValuationHistory(
            ledger_id="main",
            portfolio_name="Personal",
            snapshots=(foreign_ledger,),
        )
    with pytest.raises(ValueError, match="history portfolio_name"):
        PortfolioValuationHistory(
            ledger_id="main",
            portfolio_name="Personal",
            snapshots=(foreign_portfolio,),
        )


def test_empty_history_is_valid() -> None:
    history = PortfolioValuationHistory(
        ledger_id="main",
        portfolio_name="Personal",
        snapshots=(),
    )

    assert history.snapshots == ()
