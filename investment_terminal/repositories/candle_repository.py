"""
SQLite repository for historical market candles.
"""

from contextlib import contextmanager
from datetime import datetime
from math import isfinite
from numbers import Real
import sqlite3

from investment_terminal.database.database import Database
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.base_repository import (
    BaseRepository,
)


class CandleConflictError(sqlite3.IntegrityError):
    """An existing candle key has a different persisted payload."""


class CandleRepository(BaseRepository):
    """
    Persist and retrieve historical OHLCV candles.
    """

    def __init__(
        self,
        database: Database,
    ) -> None:
        self.database = database

    def save(
        self,
        model: Candle,
    ) -> int:
        """
        Save one candle and return its database ID.

        Exact repeats return the existing ID; changed payloads fail closed.
        """
        self._validate_candle(model)

        values = self._candle_values(model)
        with self._write_transaction():
            candle_id, _ = self._save_values(values)
        return candle_id

    def save_many(
        self,
        candles: list[Candle],
    ) -> int:
        """
        Save multiple candles in one transaction.

        Only exact duplicates are ignored; conflicts roll back the entire batch.

        Returns the number of newly inserted rows.
        """
        if not isinstance(candles, list):
            raise TypeError(
                "candles must be a list"
            )

        if not candles:
            return 0

        for candle in candles:
            self._validate_candle(candle)

        values = [self._candle_values(candle) for candle in candles]
        inserted = 0
        with self._write_transaction():
            for value in values:
                _, was_inserted = self._save_values(value)
                inserted += was_inserted
        return inserted

    @contextmanager
    def _write_transaction(self):
        """Own one transaction; never commit or roll back a caller's work."""
        connection = self.database.connection
        if connection.in_transaction:
            raise RuntimeError("Candle writes require an idle connection")
        with connection:
            # Serialize conflict checks with writes, including exact replays.
            connection.execute("BEGIN IMMEDIATE")
            yield

    def _save_values(self, values: tuple[object, ...]) -> tuple[int, int]:
        cursor = self.database.connection.execute(
            """
            INSERT INTO candles (
                symbol, resolution, timestamp, open_price, high_price,
                low_price, close_price, volume, currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, resolution, timestamp) DO NOTHING
            """,
            values,
        )
        if cursor.rowcount == 1:
            return int(cursor.lastrowid), 1
        row = self.database.connection.execute(
            """
            SELECT id, open_price, high_price, low_price, close_price, volume, currency
            FROM candles WHERE symbol = ? AND resolution = ? AND timestamp = ?
            """,
            values[:3],
        ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError("Candle insert did not persist a row")
        if tuple(row)[1:] != values[3:]:
            raise CandleConflictError("Existing candle payload conflicts with input")
        return int(row["id"]), 0

    def get(
        self,
        candle_id: int,
    ) -> Candle | None:
        """
        Return one candle by database ID.
        """
        self._validate_id(candle_id)

        row = self.database.connection.execute(
            """
            SELECT
                symbol,
                resolution,
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                currency
            FROM candles
            WHERE id = ?
            """,
            (candle_id,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_candle(row)

    def get_latest(
        self,
        symbol: str,
        resolution: str,
    ) -> Candle | None:
        """
        Return the most recent stored candle.

        Return None when no candle exists for the requested
        symbol and resolution.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )

        row = self.database.connection.execute(
            """
            SELECT
                symbol,
                resolution,
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                currency
            FROM candles
            WHERE symbol = ?
              AND resolution = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (
                normalized_symbol,
                normalized_resolution,
            ),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_candle(row)

    def get_earliest(
        self,
        symbol: str,
        resolution: str,
    ) -> Candle | None:
        """Return the earliest stored candle for an identity."""
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )

        row = self.database.connection.execute(
            """
            SELECT
                symbol,
                resolution,
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                currency
            FROM candles
            WHERE symbol = ?
              AND resolution = ?
            ORDER BY timestamp ASC
            LIMIT 1
            """,
            (
                normalized_symbol,
                normalized_resolution,
            ),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_candle(row)

    def get_range(
        self,
        symbol: str,
        resolution: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Candle]:
        """
        Return candles ordered by timestamp.

        Optional start and end values are inclusive.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )

        if (
            start is not None
            and not isinstance(
                start,
                datetime,
            )
        ):
            raise TypeError(
                "start must be a datetime or None"
            )

        if (
            end is not None
            and not isinstance(
                end,
                datetime,
            )
        ):
            raise TypeError(
                "end must be a datetime or None"
            )

        if (
            start is not None
            and end is not None
            and start > end
        ):
            raise ValueError(
                "start must not be later than end"
            )

        query = """
            SELECT
                symbol,
                resolution,
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                currency
            FROM candles
            WHERE symbol = ?
              AND resolution = ?
        """

        parameters: list[object] = [
            normalized_symbol,
            normalized_resolution,
        ]

        if start is not None:
            query += " AND timestamp >= ?"
            parameters.append(
                start.isoformat()
            )

        if end is not None:
            query += " AND timestamp <= ?"
            parameters.append(
                end.isoformat()
            )

        query += " ORDER BY timestamp ASC"

        rows = self.database.connection.execute(
            query,
            parameters,
        ).fetchall()

        return [
            self._row_to_candle(row)
            for row in rows
        ]

    def delete(
        self,
        candle_id: int,
    ) -> bool:
        """
        Delete one candle by ID.
        """
        self._validate_id(candle_id)

        cursor = self.database.connection.execute(
            """
            DELETE FROM candles
            WHERE id = ?
            """,
            (candle_id,),
        )
        self.database.connection.commit()

        return cursor.rowcount == 1

    def count(
        self,
        symbol: str,
        resolution: str,
    ) -> int:
        """
        Count stored candles for a symbol and resolution.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )

        row = self.database.connection.execute(
            """
            SELECT COUNT(*) AS candle_count
            FROM candles
            WHERE symbol = ?
              AND resolution = ?
            """,
            (
                normalized_symbol,
                normalized_resolution,
            ),
        ).fetchone()

        return int(
            row["candle_count"]
        )

    @staticmethod
    def _candle_values(
        candle: Candle,
    ) -> tuple[object, ...]:
        return (
            candle.symbol.strip().upper(),
            candle.resolution.strip().upper(),
            candle.timestamp.isoformat(),
            float(candle.open_price),
            float(candle.high_price),
            float(candle.low_price),
            float(candle.close_price),
            float(candle.volume),
            candle.currency.strip().upper(),
        )

    @staticmethod
    def _row_to_candle(
        row: sqlite3.Row,
    ) -> Candle:
        return Candle(
            symbol=row["symbol"],
            resolution=row["resolution"],
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            open_price=row["open_price"],
            high_price=row["high_price"],
            low_price=row["low_price"],
            close_price=row["close_price"],
            volume=row["volume"],
            currency=row["currency"],
        )

    @classmethod
    def _validate_candle(
        cls,
        candle: Candle,
    ) -> None:
        if not isinstance(
            candle,
            Candle,
        ):
            raise TypeError(
                "model must be a Candle instance"
            )

        cls._normalize_text(
            candle.symbol,
            field_name="symbol",
        )
        cls._normalize_text(
            candle.resolution,
            field_name="resolution",
        )
        cls._normalize_text(
            candle.currency,
            field_name="currency",
        )

        if not isinstance(
            candle.timestamp,
            datetime,
        ):
            raise ValueError(
                "candle timestamp must be a datetime"
            )

        numeric_fields = {
            "open_price": candle.open_price,
            "high_price": candle.high_price,
            "low_price": candle.low_price,
            "close_price": candle.close_price,
            "volume": candle.volume,
        }

        for (
            field_name,
            value,
        ) in numeric_fields.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not isfinite(float(value))
            ):
                raise ValueError(
                    f"{field_name} must be "
                    "a finite number"
                )

        if candle.open_price <= 0:
            raise ValueError(
                "open_price must be greater than zero"
            )

        if candle.high_price <= 0:
            raise ValueError(
                "high_price must be greater than zero"
            )

        if candle.low_price <= 0:
            raise ValueError(
                "low_price must be greater than zero"
            )

        if candle.close_price <= 0:
            raise ValueError(
                "close_price must be greater than zero"
            )

        if candle.volume < 0:
            raise ValueError(
                "volume must not be negative"
            )

        if candle.high_price < max(
            candle.open_price,
            candle.close_price,
            candle.low_price,
        ):
            raise ValueError(
                "high_price must be "
                "the highest OHLC value"
            )

        if candle.low_price > min(
            candle.open_price,
            candle.close_price,
            candle.high_price,
        ):
            raise ValueError(
                "low_price must be "
                "the lowest OHLC value"
            )

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be "
                "a non-empty string"
            )

        return value.strip().upper()

    @staticmethod
    def _validate_id(
        candle_id: int,
    ) -> None:
        if (
            isinstance(candle_id, bool)
            or not isinstance(
                candle_id,
                int,
            )
            or candle_id <= 0
        ):
            raise ValueError(
                "candle_id must be "
                "a positive integer"
            )
