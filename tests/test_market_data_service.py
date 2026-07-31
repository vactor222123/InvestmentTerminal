"""
Tests for the market data service.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.models.quote import Quote
from investment_terminal.services.market_data_service import (
    MarketDataService,
)


def create_quote() -> Quote:
    return Quote(
        symbol="MSFT",
        price=412.75,
        currency="USD",
        timestamp=datetime(
            2026,
            8,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_download_and_save_quote_returns_saved_quote() -> None:
    quote = create_quote()

    client = Mock()
    repository = Mock()

    client.get_quote.return_value = quote
    repository.save.return_value = 42
    repository.get.return_value = quote

    service = MarketDataService(
        client=client,
        repository=repository,
    )

    result = service.download_and_save_quote("msft")

    assert result.quote_id == 42
    assert result.quote == quote

    client.get_quote.assert_called_once_with(
        symbol="msft",
        currency="USD",
    )
    repository.save.assert_called_once_with(quote)
    repository.get.assert_called_once_with(42)


def test_download_and_save_quote_passes_currency() -> None:
    quote = Quote(
        symbol="SAP.DE",
        price=210.50,
        currency="EUR",
        timestamp=datetime.now(timezone.utc),
    )

    client = Mock()
    repository = Mock()

    client.get_quote.return_value = quote
    repository.save.return_value = 7
    repository.get.return_value = quote

    service = MarketDataService(
        client=client,
        repository=repository,
    )

    service.download_and_save_quote(
        symbol="SAP.DE",
        currency="EUR",
    )

    client.get_quote.assert_called_once_with(
        symbol="SAP.DE",
        currency="EUR",
    )


def test_download_and_save_quote_rejects_missing_saved_record() -> None:
    quote = create_quote()

    client = Mock()
    repository = Mock()

    client.get_quote.return_value = quote
    repository.save.return_value = 42
    repository.get.return_value = None

    service = MarketDataService(
        client=client,
        repository=repository,
    )

    with pytest.raises(RuntimeError, match="could not be read back"):
        service.download_and_save_quote("MSFT")


def test_download_and_save_quote_rejects_changed_record() -> None:
    quote = create_quote()

    changed_quote = Quote(
        symbol="MSFT",
        price=1.0,
        currency="USD",
        timestamp=quote.timestamp,
    )

    client = Mock()
    repository = Mock()

    client.get_quote.return_value = quote
    repository.save.return_value = 42
    repository.get.return_value = changed_quote

    service = MarketDataService(
        client=client,
        repository=repository,
    )

    with pytest.raises(RuntimeError, match="changed"):
        service.download_and_save_quote("MSFT")