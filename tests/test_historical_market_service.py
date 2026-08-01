"""
Tests for HistoricalMarketService.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.models.candle import Candle
from investment_terminal.services.historical_market_service import (
    HistoricalMarketService,
)


def create_candles() -> list[Candle]:
    start = datetime(
        2026,
        7,
        1,
        tzinfo=timezone.utc,
    )

    return [
        Candle(
            symbol="MSFT",
            resolution="D",
            timestamp=start + timedelta(days=index),
            open_price=100.0 + index,
            high_price=105.0 + index,
            low_price=98.0 + index,
            close_price=103.0 + index,
            volume=1_000_000 + index,
            currency="USD",
        )
        for index in range(3)
    ]


def create_period() -> tuple[datetime, datetime]:
    return (
        datetime(
            2026,
            7,
            1,
            tzinfo=timezone.utc,
        ),
        datetime(
            2026,
            7,
            10,
            tzinfo=timezone.utc,
        ),
    )


def test_import_candles_returns_statistics() -> None:
    candles = create_candles()
    start, end = create_period()

    client = Mock()
    repository = Mock()

    client.get_candles.return_value = candles
    repository.save_many.return_value = 3
    repository.count.return_value = 3

    service = HistoricalMarketService(
        client=client,
        repository=repository,
    )

    result = service.import_candles(
        symbol="msft",
        resolution="d",
        start=start,
        end=end,
    )

    assert result.symbol == "MSFT"
    assert result.resolution == "D"
    assert result.downloaded == 3
    assert result.inserted == 3
    assert result.duplicates == 0
    assert result.stored_total == 3
    assert result.start == start
    assert result.end == end

    client.get_candles.assert_called_once_with(
        symbol="msft",
        resolution="d",
        start=start,
        end=end,
        currency="USD",
    )
    repository.save_many.assert_called_once_with(candles)
    repository.count.assert_called_once_with(
        "MSFT",
        "D",
    )


def test_import_candles_reports_duplicates() -> None:
    candles = create_candles()
    start, end = create_period()

    client = Mock()
    repository = Mock()

    client.get_candles.return_value = candles
    repository.save_many.return_value = 1
    repository.count.return_value = 10

    service = HistoricalMarketService(
        client=client,
        repository=repository,
    )

    result = service.import_candles(
        symbol="MSFT",
        resolution="D",
        start=start,
        end=end,
    )

    assert result.downloaded == 3
    assert result.inserted == 1
    assert result.duplicates == 2
    assert result.stored_total == 10


def test_import_candles_handles_no_data() -> None:
    start, end = create_period()

    client = Mock()
    repository = Mock()

    client.get_candles.return_value = []
    repository.save_many.return_value = 0
    repository.count.return_value = 25

    service = HistoricalMarketService(
        client=client,
        repository=repository,
    )

    result = service.import_candles(
        symbol="MSFT",
        resolution="D",
        start=start,
        end=end,
    )

    assert result.downloaded == 0
    assert result.inserted == 0
    assert result.duplicates == 0
    assert result.stored_total == 25

    repository.save_many.assert_called_once_with([])


def test_import_candles_passes_currency() -> None:
    start, end = create_period()

    client = Mock()
    repository = Mock()

    client.get_candles.return_value = []
    repository.save_many.return_value = 0
    repository.count.return_value = 0

    service = HistoricalMarketService(
        client=client,
        repository=repository,
    )

    service.import_candles(
        symbol="SAP.DE",
        resolution="D",
        start=start,
        end=end,
        currency="EUR",
    )

    client.get_candles.assert_called_once_with(
        symbol="SAP.DE",
        resolution="D",
        start=start,
        end=end,
        currency="EUR",
    )


@pytest.mark.parametrize(
    ("inserted", "downloaded"),
    [
        (-1, 3),
        (4, 3),
    ],
)
def test_import_candles_rejects_invalid_insert_count(
    inserted: int,
    downloaded: int,
) -> None:
    candles = create_candles()[:downloaded]
    start, end = create_period()

    client = Mock()
    repository = Mock()

    client.get_candles.return_value = candles
    repository.save_many.return_value = inserted

    service = HistoricalMarketService(
        client=client,
        repository=repository,
    )

    with pytest.raises(
        RuntimeError,
        match="invalid inserted count",
    ):
        service.import_candles(
            symbol="MSFT",
            resolution="D",
            start=start,
            end=end,
        )