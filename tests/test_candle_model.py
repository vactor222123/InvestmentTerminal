"""
Tests for the historical Candle model and database schema.
"""

from datetime import datetime, timezone
import sqlite3

import pytest

from investment_terminal.database.database import Database
from investment_terminal.models.candle import Candle
from investment_terminal.config.settings import Settings    


def create_candle() -> Candle:
    return Candle(
        symbol="MSFT",
        resolution="D",
        timestamp=datetime(
            2026,
            7,
            31,
            20,
            0,
            tzinfo=timezone.utc,
        ),
        open_price=470.0,
        high_price=475.0,
        low_price=460.0,
        close_price=464.72,
        volume=25_000_000,
        currency="USD",
    )


def test_candle_model_contains_ohlcv_values() -> None:
    candle = create_candle()

    assert candle.symbol == "MSFT"
    assert candle.resolution == "D"
    assert candle.open_price == 470.0
    assert candle.high_price == 475.0
    assert candle.low_price == 460.0
    assert candle.close_price == 464.72
    assert candle.volume == 25_000_000
    assert candle.currency == "USD"
    assert candle.timestamp is not None


def test_database_creates_candles_table() -> None:
    database = Database()
    database.initialize()

    try:
        row = database.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'candles'
            """
        ).fetchone()

        assert row is not None
        assert row["name"] == "candles"
    finally:
        database.close()


def test_candles_table_rejects_duplicate_candle(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        tmp_path / "candles.db",
    )

    database = Database()
    database.initialize()

    candle = create_candle()

    values = (
        candle.symbol,
        candle.resolution,
        candle.timestamp.isoformat(),
        candle.open_price,
        candle.high_price,
        candle.low_price,
        candle.close_price,
        candle.volume,
        candle.currency,
    )

    try:
        database.connection.execute(
            """
            INSERT INTO candles (
                symbol,
                resolution,
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                currency
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        database.connection.commit()

        with pytest.raises(sqlite3.IntegrityError):
            database.connection.execute(
                """
                INSERT INTO candles (
                    symbol,
                    resolution,
                    timestamp,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    currency
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            database.connection.commit()
    finally:
        database.close()