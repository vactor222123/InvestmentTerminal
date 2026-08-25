"""Tests for durable SQLite portfolio transaction storage."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.transaction_ledger_models import PortfolioTransaction
from investment_terminal.portfolio.transaction_ledger_repository import PortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import SQLitePortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_store import PortfolioTransactionSQLiteStore


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def asset(symbol: str = "WORLD", isin: str = "IE00B4L5Y983") -> InstrumentIdentity:
    return InstrumentIdentity(symbol=symbol, name=f"{symbol} ETF", instrument_type="ETF", currency="EUR", isin=isin)


def tx(transaction_id: str, day: int = 1, instrument: InstrumentIdentity | None = None) -> PortfolioTransaction:
    return PortfolioTransaction(transaction_id=transaction_id, transaction_type="BUY", occurred_at=ts(day), settlement_currency="EUR", instrument=instrument or asset(), quantity=2.5, unit_price=100.0)


def store(path: Path) -> PortfolioTransactionSQLiteStore:
    return PortfolioTransactionSQLiteStore(path, ledger_id="main", portfolio_name="Personal", base_currency="eur")


def repo(path: Path) -> SQLitePortfolioTransactionRepository:
    result = SQLitePortfolioTransactionRepository(store(path))
    assert isinstance(result, PortfolioTransactionRepository)
    return result


def test_store_initializes_versioned_schema(tmp_path: Path) -> None:
    value = store(tmp_path / "nested" / "transactions.db")
    assert value.initialize().exists()
    assert value.schema_version() == 1


def test_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    value = store(tmp_path / "transactions.db")
    with pytest.raises(RuntimeError):
        with value.transaction() as connection:
            connection.execute("INSERT INTO portfolio_transactions VALUES (?, ?, ?, ?)", ("tx-1", ts(1).isoformat(), None, "{}"))
            raise RuntimeError("interrupt")
    with value.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM portfolio_transactions").fetchone()[0] == 0


def test_repository_round_trip_survives_recreation(tmp_path: Path) -> None:
    database = tmp_path / "transactions.db"
    expected = tx("tx-1")
    repo(database).add(expected)
    recreated = repo(database)
    assert recreated.require("tx-1") == expected
    assert recreated.snapshot().transactions == (expected,)


def test_duplicate_is_rejected_and_original_preserved(tmp_path: Path) -> None:
    repository = repo(tmp_path / "transactions.db")
    original = tx("tx-1", 1)
    repository.add(original)
    with pytest.raises(ValueError, match="identity already exists"):
        repository.add(tx("tx-1", 2))
    assert repository.require("tx-1") == original


def test_batch_append_reports_new_existing_and_repeated_rows(tmp_path: Path) -> None:
    repository = repo(tmp_path / "transactions.db")
    original = tx("existing", 1)
    new = tx("new", 2)
    repository.add(original)

    assert repository.add_batch((new, tx("existing", 3), new)) == (
        True,
        False,
        False,
    )
    assert repository.require("existing") == original
    assert repository.require("new") == new

    assert repository.add_batch((new, original)) == (False, False)
    assert repo(tmp_path / "transactions.db").list_all() == (original, new)


def test_batch_append_rolls_back_after_later_unexpected_failure(
    tmp_path: Path,
) -> None:
    database = tmp_path / "transactions.db"
    value = store(database)
    value.initialize()
    with value.connect() as connection:
        connection.execute(
            "CREATE TRIGGER fail_second_transaction "
            "BEFORE INSERT ON portfolio_transactions "
            "WHEN NEW.transaction_id = 'fail' "
            "BEGIN SELECT RAISE(ABORT, 'simulated persistence failure'); END"
        )
        connection.commit()

    with pytest.raises(sqlite3.IntegrityError, match="simulated persistence failure"):
        SQLitePortfolioTransactionRepository(value).add_batch(
            (tx("candidate", 1), tx("fail", 2))
        )

    recreated = repo(database)
    assert recreated.get("candidate") is None
    assert recreated.get("fail") is None


def test_batch_failure_preserves_preexisting_transaction(tmp_path: Path) -> None:
    database = tmp_path / "transactions.db"
    original = tx("original", 1)
    repository = repo(database)
    repository.add(original)
    with repository.store.connect() as connection:
        connection.execute(
            "CREATE TRIGGER fail_later_transaction "
            "BEFORE INSERT ON portfolio_transactions "
            "WHEN NEW.transaction_id = 'fail' "
            "BEGIN SELECT RAISE(ABORT, 'simulated persistence failure'); END"
        )
        connection.commit()

    with pytest.raises(sqlite3.IntegrityError):
        repository.add_batch((tx("candidate", 2), tx("original", 3), tx("fail", 4)))

    recreated = repo(database)
    assert recreated.list_all() == (original,)


def test_queries_match_repository_contract(tmp_path: Path) -> None:
    repository = repo(tmp_path / "transactions.db")
    emerging = asset("EM", "IE00BKM4GZ66")
    first = tx("tx-1", 1)
    second = tx("tx-2", 2, emerging)
    third = tx("tx-3", 3)
    for item in (third, second, first):
        repository.add(item)
    assert repository.list_all() == (first, second, third)
    assert repository.list_between(ts(1), ts(3)) == (first, second)
    assert repository.list_for_instrument("ie00b4l5y983") == (first, third)


def test_store_rejects_mismatched_ledger_metadata(tmp_path: Path) -> None:
    database = tmp_path / "transactions.db"
    store(database).initialize()
    other = PortfolioTransactionSQLiteStore(database, ledger_id="other", portfolio_name="Personal", base_currency="EUR")
    with pytest.raises(RuntimeError, match="metadata"):
        other.initialize()


def test_corrupt_payload_fails_visible_on_read(tmp_path: Path) -> None:
    value = store(tmp_path / "transactions.db")
    value.initialize()
    with value.transaction() as connection:
        connection.execute("INSERT INTO portfolio_transactions VALUES (?, ?, ?, ?)", ("bad", ts(1).isoformat(), None, "not-json"))
    with pytest.raises(Exception):
        SQLitePortfolioTransactionRepository(value).require("bad")
