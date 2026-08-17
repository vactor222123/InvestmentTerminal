"""Tests for append-only portfolio transaction repository semantics."""

from datetime import datetime, timezone

import pytest

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransaction,
)
from investment_terminal.portfolio.transaction_ledger_repository import (
    InMemoryPortfolioTransactionRepository,
    PortfolioTransactionRepository,
)


def timestamp(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=timezone.utc)


def instrument(symbol: str, isin: str) -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=symbol,
        name=f"{symbol} ETF",
        instrument_type="ETF",
        currency="EUR",
        isin=isin,
    )


WORLD = instrument("WORLD", "IE00B4L5Y983")
EM = instrument("EM", "IE00BKM4GZ66")


def transaction(
    transaction_id: str,
    *,
    day: int,
    asset: InstrumentIdentity = WORLD,
) -> PortfolioTransaction:
    return PortfolioTransaction(
        transaction_id=transaction_id,
        transaction_type="BUY",
        occurred_at=timestamp(day),
        settlement_currency="EUR",
        instrument=asset,
        quantity=1.0,
        unit_price=100.0,
    )


def repository() -> InMemoryPortfolioTransactionRepository:
    result = InMemoryPortfolioTransactionRepository(
        ledger_id="main",
        portfolio_name="Personal",
        base_currency="eur",
    )
    assert isinstance(result, PortfolioTransactionRepository)
    return result


def test_add_get_and_require_exact_transaction() -> None:
    repo = repository()
    expected = transaction("tx-1", day=1)

    assert repo.add(expected) is expected
    assert repo.get(" tx-1 ") is expected
    assert repo.require("tx-1") is expected
    assert repo.get("missing") is None


def test_require_rejects_missing_transaction() -> None:
    with pytest.raises(KeyError, match="No portfolio transaction"):
        repository().require("missing")


def test_duplicate_identity_is_rejected_and_original_is_preserved() -> None:
    repo = repository()
    original = transaction("tx-1", day=1)
    repo.add(original)

    with pytest.raises(ValueError, match="identity already exists"):
        repo.add(transaction("tx-1", day=2))

    assert repo.require("tx-1") is original


def test_add_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="PortfolioTransaction"):
        repository().add(object())  # type: ignore[arg-type]


def test_list_all_is_deterministic_independent_of_insertion_order() -> None:
    repo = repository()
    later_b = transaction("tx-b", day=2)
    earlier = transaction("tx-z", day=1)
    later_a = transaction("tx-a", day=2)

    for item in (later_b, earlier, later_a):
        repo.add(item)

    assert repo.list_all() == (earlier, later_a, later_b)


def test_list_between_uses_half_open_interval() -> None:
    repo = repository()
    first = transaction("tx-1", day=1)
    second = transaction("tx-2", day=2)
    third = transaction("tx-3", day=3)
    for item in (first, second, third):
        repo.add(item)

    assert repo.list_between(timestamp(1), timestamp(3)) == (
        first,
        second,
    )


def test_list_between_rejects_naive_or_reversed_boundaries() -> None:
    repo = repository()
    with pytest.raises(ValueError, match="timezone-aware"):
        repo.list_between(datetime(2026, 8, 1), timestamp(2))
    with pytest.raises(ValueError, match="later than"):
        repo.list_between(timestamp(2), timestamp(1))


def test_list_for_instrument_excludes_other_assets_and_portfolio_fees() -> None:
    repo = repository()
    world = transaction("world", day=1)
    emerging = transaction("em", day=2, asset=EM)
    fee = PortfolioTransaction(
        transaction_id="fee",
        transaction_type="FEE",
        occurred_at=timestamp(3),
        settlement_currency="EUR",
        cash_amount=1.0,
    )
    for item in (fee, emerging, world):
        repo.add(item)

    assert repo.list_for_instrument(" ie00b4l5y983 ") == (world,)


def test_snapshot_returns_normalized_immutable_ledger_projection() -> None:
    repo = repository()
    second = transaction("tx-2", day=2)
    first = transaction("tx-1", day=1)
    repo.add(second)
    repo.add(first)

    ledger = repo.snapshot()

    assert ledger.ledger_id == "main"
    assert ledger.base_currency == "EUR"
    assert ledger.transactions == (first, second)
