"""Regression tests for audit A01/A04; all data is synthetic."""

from dataclasses import replace
from datetime import timedelta
import sqlite3

import pytest

from investment_terminal.repositories.candle_repository import CandleConflictError
from investment_terminal.services.historical_market_service import HistoricalMarketService
from investment_terminal.services.projected_historical_market_service import (
    ProjectedHistoricalMarketService,
)
from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from tests.test_candle_repository import create_candle, repository


@pytest.mark.parametrize("method", ["save", "save_many"])
@pytest.mark.parametrize("field,value", [
    ("open_price", 98), ("high_price", 103), ("low_price", 96),
    ("close_price", 101), ("volume", 5), ("currency", "EUR"),
])
def test_conflict_is_typed_and_preserves_original(repository, method, field, value):
    original = create_candle()
    original_id = repository.save(original)
    changed = replace(original, **{field: value})
    with pytest.raises(CandleConflictError, match="payload conflicts"):
        getattr(repository, method)(changed if method == "save" else [changed])
    assert repository.get(original_id) == original
    assert not repository.database.connection.in_transaction
    assert repository.save(original) == original_id


def test_exact_normalized_repeats_have_stable_id_and_count(repository):
    original = create_candle()
    equivalent = replace(original, symbol=" msft ", resolution=" d ", currency=" usd ")
    assert repository.save_many([original, equivalent, original]) == 1
    original_id = repository.save(original)
    assert repository.save(equivalent) == original_id
    assert repository.save_many([equivalent]) == 0
    assert not repository.database.connection.in_transaction


@pytest.mark.parametrize("preexisting", [False, True])
def test_batch_conflict_rolls_back_new_prefix(repository, preexisting):
    original = create_candle()
    if preexisting:
        repository.save(original)
    batch = [create_candle(1), original, replace(original, currency="EUR")]
    with pytest.raises(CandleConflictError):
        repository.save_many(batch)
    assert repository.count("MSFT", "D") == int(preexisting)
    assert not repository.database.connection.in_transaction
    repository.save(create_candle(2))
    assert repository.count("MSFT", "D") == 1 + int(preexisting)


@pytest.mark.parametrize("method", ["save", "save_many"])
def test_constraint_failure_cannot_leak_into_later_commit(repository, method):
    connection = repository.database.connection
    connection.execute(
        "CREATE TRIGGER fail_candle BEFORE INSERT ON candles WHEN NEW.symbol = 'FAIL' "
        "BEGIN SELECT RAISE(ABORT, 'synthetic insert failure'); END"
    )
    bad = create_candle(symbol="FAIL")
    with pytest.raises(sqlite3.IntegrityError, match="synthetic insert failure"):
        getattr(repository, method)(bad if method == "save" else [create_candle(), bad])
    assert not connection.in_transaction
    assert repository.count("MSFT", "D") == 0
    repository.save(create_candle(1))
    assert repository.count("MSFT", "D") == 1


@pytest.mark.parametrize("method", ["save", "save_many"])
def test_commit_failure_rolls_back(repository, method):
    connection = repository.database.connection
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        "CREATE TABLE parent (id INTEGER PRIMARY KEY);"
        "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id) "
        "DEFERRABLE INITIALLY DEFERRED);"
        "CREATE TRIGGER fail_commit AFTER INSERT ON candles BEGIN "
        "INSERT INTO child VALUES (123); END;"
    )
    original = create_candle()
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        getattr(repository, method)(original if method == "save" else [original, create_candle(1)])
    assert not connection.in_transaction
    assert repository.count("MSFT", "D") == 0
    assert connection.execute("SELECT COUNT(*) FROM child").fetchone()[0] == 0
    connection.execute("DROP TRIGGER fail_commit")
    assert repository.save_many([original]) == 1


@pytest.mark.parametrize("method", ["save", "save_many"])
def test_existing_transaction_is_not_committed_or_rolled_back(repository, method):
    connection = repository.database.connection
    connection.execute("CREATE TABLE caller_work (value INTEGER)")
    connection.execute("INSERT INTO caller_work VALUES (7)")
    candle = create_candle()
    with pytest.raises(RuntimeError, match="idle connection"):
        getattr(repository, method)(candle if method == "save" else [candle])
    assert connection.in_transaction
    assert connection.execute("SELECT value FROM caller_work").fetchone()[0] == 7
    assert repository.count("MSFT", "D") == 0
    connection.rollback()
    assert connection.execute("SELECT COUNT(*) FROM caller_work").fetchone()[0] == 0


def test_invalid_batch_validates_before_any_write(repository):
    with pytest.raises(ValueError, match="high_price"):
        repository.save_many([create_candle(), replace(create_candle(1), high_price=1)])
    assert repository.count("MSFT", "D") == 0
    assert not repository.database.connection.in_transaction
    assert repository.save_many([]) == 0


def test_write_lock_failure_does_not_touch_other_connection(repository):
    connection = repository.database.connection
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    other = sqlite3.connect(path)
    connection.execute("PRAGMA busy_timeout = 0")
    try:
        other.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            repository.save(create_candle())
        assert other.in_transaction
        assert not connection.in_transaction
        assert repository.count("MSFT", "D") == 0
        other.rollback()
        assert repository.save_many([create_candle()]) == 1
    finally:
        other.close()


@pytest.mark.parametrize("service_type", [HistoricalMarketService, ProjectedHistoricalMarketService])
def test_import_conflict_is_not_reported_as_duplicate_success(repository, service_type):
    original = create_candle()
    repository.save(original)

    class Client:
        def get_candles(self, **kwargs):
            return [create_candle(1), replace(original, currency="EUR")]

        def get_candle_projection(self, **kwargs):
            return YahooCandleProjection(tuple(self.get_candles()), 0, ())

    service = service_type(Client(), repository)
    with pytest.raises(CandleConflictError):
        service.import_candles("MSFT", "D", original.timestamp,
                               original.timestamp + timedelta(days=2))
    assert repository.get_range("MSFT", "D") == [original]


def test_non_key_constraint_is_not_ignored_on_exact_repeat(repository):
    original = create_candle()
    original_id = repository.save(original)
    repository.database.connection.execute(
        "CREATE TRIGGER deny_repeat BEFORE INSERT ON candles "
        "BEGIN SELECT RAISE(ABORT, 'synthetic policy'); END"
    )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic policy"):
        repository.save(original)
    assert repository.get(original_id) == original
    assert not repository.database.connection.in_transaction
