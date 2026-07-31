from datetime import datetime, timezone

import pytest

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.models.quote import Quote
from investment_terminal.repositories.quote_repository import QuoteRepository


@pytest.fixture
def repository(tmp_path, monkeypatch):
    """
    Create an initialized repository backed by a temporary SQLite database.
    """
    monkeypatch.setattr(Settings, "DATABASE_PATH", tmp_path / "quotes.db")
    database = Database()
    database.initialize()

    yield QuoteRepository(database)

    database.close()


def test_save_and_get_quote(repository):
    """
    A saved quote can be read back with its original values.
    """
    timestamp = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
    quote_id = repository.save(
        Quote(symbol="AAPL", price=210.50, currency="USD", timestamp=timestamp)
    )

    quote = repository.get(quote_id)

    assert quote == Quote(symbol="AAPL", price=210.50, currency="USD", timestamp=timestamp)


def test_get_all_quotes_returns_quotes_in_insert_order(repository):
    """
    All quotes are returned in their insertion order.
    """
    first = Quote(symbol="AAPL", price=210.50, timestamp=datetime(2026, 7, 31, 12, 0))
    second = Quote(symbol="MSFT", price=510.25, timestamp=datetime(2026, 7, 31, 12, 1))

    repository.save(first)
    repository.save(second)

    assert repository.get_all() == [first, second]


def test_update_quote_replaces_existing_values(repository):
    """
    Updating an existing quote persists its replacement values.
    """
    quote_id = repository.save(
        Quote(symbol="AAPL", price=210.50, timestamp=datetime(2026, 7, 31, 12, 0))
    )
    updated_quote = Quote(
        symbol="AAPL",
        price=211.75,
        currency="USD",
        timestamp=datetime(2026, 7, 31, 12, 5),
    )

    assert repository.update(quote_id, updated_quote) is True
    assert repository.get(quote_id) == updated_quote
    assert repository.update(999, updated_quote) is False


def test_delete_quote_removes_existing_quote(repository):
    """
    Deleting an existing quote removes it from the repository.
    """
    quote_id = repository.save(
        Quote(symbol="AAPL", price=210.50, timestamp=datetime(2026, 7, 31, 12, 0))
    )

    assert repository.delete(quote_id) is True
    assert repository.get(quote_id) is None
    assert repository.delete(quote_id) is False


def test_save_rejects_quote_without_timestamp(repository):
    """
    A quote must provide the non-null timestamp required by SQLite.
    """
    with pytest.raises(ValueError, match="timestamp"):
        repository.save(Quote(symbol="AAPL", price=210.50))
