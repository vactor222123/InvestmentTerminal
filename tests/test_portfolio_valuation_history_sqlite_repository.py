"""Tests for durable SQLite portfolio valuation history."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.portfolio_valuation_history import (
    PortfolioValuationSnapshot,
)
from investment_terminal.portfolio.portfolio_valuation_history_repository import (
    PortfolioValuationHistoryRepository,
)
from investment_terminal.portfolio.portfolio_valuation_history_sqlite_repository import (
    SQLitePortfolioValuationHistoryRepository,
)
from investment_terminal.portfolio.portfolio_valuation_history_sqlite_store import (
    PortfolioValuationHistorySQLiteStore,
)
from investment_terminal.portfolio.realized_performance import (
    RealizedCurrencySummary,
    RealizedPerformance,
    RealizedSale,
)
from investment_terminal.portfolio.unrealized_performance import (
    UnrealizedCurrencySummary,
    UnrealizedPerformance,
    UnrealizedPositionPerformance,
)

WORLD = InstrumentIdentity(
    symbol="WORLD",
    name="World ETF",
    instrument_type="ETF",
    currency="EUR",
    isin="IE00B4L5Y983",
    exchange_ticker="VWCE.DE",
    exchange_code="XETR",
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def snapshot(
    snapshot_id: str,
    day: int = 2,
    *,
    ledger_id: str = "main",
    portfolio_name: str = "Personal"
) -> PortfolioValuationSnapshot:
    unrealized = UnrealizedPerformance(
        ledger_id=ledger_id,
        portfolio_name=portfolio_name,
        valued_at=ts(day),
        positions=(
            UnrealizedPositionPerformance(
                instrument=WORLD,
                quantity=2,
                average_cost=100,
                cost_basis=200,
                market_price=125,
                market_value=250,
                unrealized_gain_loss=50,
                currency="EUR",
                unrealized_return_percent=25,
                quoted_at=ts(day),
                quote_source="test",
            ),
        ),
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
    realized = RealizedPerformance(
        ledger_id=ledger_id,
        portfolio_name=portfolio_name,
        sales=(
            RealizedSale(
                sell_transaction_id="sell-1",
                occurred_at=ts(1),
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
    return PortfolioValuationSnapshot.build(
        snapshot_id=snapshot_id, unrealized=unrealized, realized=realized
    )


def store(
    path: Path, *, ledger_id: str = "main"
) -> PortfolioValuationHistorySQLiteStore:
    return PortfolioValuationHistorySQLiteStore(
        path, ledger_id=ledger_id, portfolio_name="Personal"
    )


def repo(path: Path) -> SQLitePortfolioValuationHistoryRepository:
    result = SQLitePortfolioValuationHistoryRepository(store(path))
    assert isinstance(result, PortfolioValuationHistoryRepository)
    return result


def test_store_initializes_versioned_schema(tmp_path: Path) -> None:
    value = store(tmp_path / "nested" / "valuations.db")
    assert value.initialize().exists()
    assert value.schema_version() == 1


def test_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    value = store(tmp_path / "valuations.db")
    with pytest.raises(RuntimeError):
        with value.transaction() as connection:
            connection.execute(
                "INSERT INTO portfolio_valuation_snapshots VALUES (?, ?, ?)",
                ("v-1", ts(1).isoformat(), "{}"),
            )
            raise RuntimeError("interrupt")
    with value.connect() as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM portfolio_valuation_snapshots"
            ).fetchone()[0]
            == 0
        )


def test_full_snapshot_round_trip_survives_recreation(tmp_path: Path) -> None:
    database = tmp_path / "valuations.db"
    expected = snapshot("v-1")
    repo(database).add(expected)
    recreated = repo(database)
    assert recreated.require("v-1") == expected
    assert recreated.require("v-1").to_dict() == expected.to_dict()
    assert recreated.history().snapshots == (expected,)


def test_duplicate_is_rejected_and_original_preserved(tmp_path: Path) -> None:
    repository = repo(tmp_path / "valuations.db")
    original = snapshot("v-1", 2)
    repository.add(original)
    with pytest.raises(ValueError, match="identity already exists"):
        repository.add(snapshot("v-1", 3))
    assert repository.require("v-1") == original


def test_queries_match_repository_contract(tmp_path: Path) -> None:
    repository = repo(tmp_path / "valuations.db")
    first, second, third = snapshot("v-1", 2), snapshot("v-2", 3), snapshot("v-3", 4)
    for item in (third, first, second):
        repository.add(item)
    assert repository.list_all() == (first, second, third)
    assert repository.list_between(ts(2), ts(4)) == (first, second)
    assert repository.list_recent(2) == (second, third)
    assert repository.latest() == third


def test_repository_rejects_invalid_limit_and_foreign_ownership(tmp_path: Path) -> None:
    repository = repo(tmp_path / "valuations.db")
    with pytest.raises(TypeError, match="integer"):
        repository.list_recent(True)
    with pytest.raises(ValueError, match="greater than zero"):
        repository.list_recent(0)
    with pytest.raises(ValueError, match="repository ledger_id"):
        repository.add(snapshot("foreign", ledger_id="other"))


def test_store_rejects_mismatched_metadata(tmp_path: Path) -> None:
    database = tmp_path / "valuations.db"
    store(database).initialize()
    with pytest.raises(RuntimeError, match="metadata"):
        store(database, ledger_id="other").initialize()


def test_corrupt_payload_fails_visible_on_read(tmp_path: Path) -> None:
    value = store(tmp_path / "valuations.db")
    value.initialize()
    with value.transaction() as connection:
        connection.execute(
            "INSERT INTO portfolio_valuation_snapshots VALUES (?, ?, ?)",
            ("bad", ts(1).isoformat(), "not-json"),
        )
    with pytest.raises(Exception):
        SQLitePortfolioValuationHistoryRepository(value).require("bad")
