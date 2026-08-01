"""
Tests for CandleRepository.
"""

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from investment_terminal.config.settings import (
    Settings,
)
from investment_terminal.database.database import (
    Database,
)
from investment_terminal.models.candle import (
    Candle,
)
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


@pytest.fixture
def repository(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        tmp_path / "candles.db",
    )

    database = Database()
    database.initialize()

    yield CandleRepository(
        database
    )

    database.close()


def create_candle(
    day_offset: int = 0,
    close_price: float = 100.0,
    symbol: str = "MSFT",
    resolution: str = "D",
) -> Candle:
    timestamp = datetime(
        2026,
        7,
        1,
        tzinfo=timezone.utc,
    ) + timedelta(
        days=day_offset
    )

    return Candle(
        symbol=symbol,
        resolution=resolution,
        timestamp=timestamp,
        open_price=close_price - 1,
        high_price=close_price + 2,
        low_price=close_price - 3,
        close_price=close_price,
        volume=(
            1_000_000
            + day_offset
        ),
        currency="USD",
    )


def test_save_and_get_candle(
    repository,
) -> None:
    candle = create_candle()

    candle_id = repository.save(
        candle
    )

    assert (
        repository.get(candle_id)
        == candle
    )


def test_save_duplicate_returns_existing_id(
    repository,
) -> None:
    candle = create_candle()

    first_id = repository.save(
        candle
    )
    second_id = repository.save(
        candle
    )

    assert first_id == second_id
    assert (
        repository.count(
            "MSFT",
            "D",
        )
        == 1
    )


def test_save_many_inserts_new_candles(
    repository,
) -> None:
    candles = [
        create_candle(
            0,
            100.0,
        ),
        create_candle(
            1,
            101.0,
        ),
        create_candle(
            2,
            102.0,
        ),
    ]

    inserted = repository.save_many(
        candles
    )

    assert inserted == 3
    assert (
        repository.count(
            "MSFT",
            "D",
        )
        == 3
    )


def test_save_many_ignores_duplicates(
    repository,
) -> None:
    candles = [
        create_candle(
            0,
            100.0,
        ),
        create_candle(
            1,
            101.0,
        ),
    ]

    assert (
        repository.save_many(candles)
        == 2
    )
    assert (
        repository.save_many(candles)
        == 0
    )
    assert (
        repository.count(
            "MSFT",
            "D",
        )
        == 2
    )


def test_get_range_returns_ordered_candles(
    repository,
) -> None:
    candles = [
        create_candle(
            2,
            102.0,
        ),
        create_candle(
            0,
            100.0,
        ),
        create_candle(
            1,
            101.0,
        ),
    ]

    repository.save_many(
        candles
    )

    result = repository.get_range(
        symbol="msft",
        resolution="d",
    )

    assert result == [
        create_candle(
            0,
            100.0,
        ),
        create_candle(
            1,
            101.0,
        ),
        create_candle(
            2,
            102.0,
        ),
    ]


def test_get_range_filters_dates(
    repository,
) -> None:
    repository.save_many(
        [
            create_candle(
                0,
                100.0,
            ),
            create_candle(
                1,
                101.0,
            ),
            create_candle(
                2,
                102.0,
            ),
        ]
    )

    start = create_candle(
        1
    ).timestamp
    end = create_candle(
        2
    ).timestamp

    result = repository.get_range(
        symbol="MSFT",
        resolution="D",
        start=start,
        end=end,
    )

    assert len(result) == 2
    assert (
        result[0].timestamp
        == start
    )
    assert (
        result[1].timestamp
        == end
    )


def test_get_latest_returns_newest_candle(
    repository,
) -> None:
    repository.save_many(
        [
            create_candle(
                2,
                102.0,
            ),
            create_candle(
                0,
                100.0,
            ),
            create_candle(
                4,
                104.0,
            ),
            create_candle(
                1,
                101.0,
            ),
        ]
    )

    result = repository.get_latest(
        symbol="msft",
        resolution="d",
    )

    assert result == create_candle(
        4,
        104.0,
    )


def test_get_latest_filters_symbol(
    repository,
) -> None:
    repository.save_many(
        [
            create_candle(
                day_offset=2,
                close_price=102.0,
                symbol="MSFT",
            ),
            create_candle(
                day_offset=5,
                close_price=205.0,
                symbol="AAPL",
            ),
        ]
    )

    result = repository.get_latest(
        symbol="MSFT",
        resolution="D",
    )

    assert result is not None
    assert result.symbol == "MSFT"
    assert (
        result.timestamp
        == create_candle(
            day_offset=2,
            close_price=102.0,
            symbol="MSFT",
        ).timestamp
    )


def test_get_latest_filters_resolution(
    repository,
) -> None:
    repository.save_many(
        [
            create_candle(
                day_offset=2,
                close_price=102.0,
                resolution="D",
            ),
            create_candle(
                day_offset=5,
                close_price=105.0,
                resolution="W",
            ),
        ]
    )

    result = repository.get_latest(
        symbol="MSFT",
        resolution="D",
    )

    assert result is not None
    assert result.resolution == "D"
    assert (
        result.timestamp
        == create_candle(
            day_offset=2,
            close_price=102.0,
            resolution="D",
        ).timestamp
    )


def test_get_latest_returns_none_when_empty(
    repository,
) -> None:
    assert (
        repository.get_latest(
            symbol="MSFT",
            resolution="D",
        )
        is None
    )


@pytest.mark.parametrize(
    ("symbol", "resolution"),
    [
        ("", "D"),
        ("   ", "D"),
        ("MSFT", ""),
        ("MSFT", "   "),
    ],
)
def test_get_latest_rejects_empty_text(
    repository,
    symbol,
    resolution,
) -> None:
    with pytest.raises(
        ValueError,
        match="non-empty string",
    ):
        repository.get_latest(
            symbol=symbol,
            resolution=resolution,
        )


def test_delete_removes_candle(
    repository,
) -> None:
    candle_id = repository.save(
        create_candle()
    )

    assert (
        repository.delete(
            candle_id
        )
        is True
    )
    assert (
        repository.get(
            candle_id
        )
        is None
    )
    assert (
        repository.delete(
            candle_id
        )
        is False
    )


def test_save_rejects_invalid_ohlc(
    repository,
) -> None:
    candle = create_candle()
    candle.high_price = 50.0

    with pytest.raises(
        ValueError,
        match="high_price",
    ):
        repository.save(
            candle
        )


def test_get_range_rejects_invalid_dates(
    repository,
) -> None:
    start = datetime(
        2026,
        7,
        2,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2026,
        7,
        1,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="start",
    ):
        repository.get_range(
            symbol="MSFT",
            resolution="D",
            start=start,
            end=end,
        )