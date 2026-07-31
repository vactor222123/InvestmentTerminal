"""
SQLite repository for market quotes.
"""

from datetime import datetime
from math import isfinite
from numbers import Real

from investment_terminal.database.database import Database
from investment_terminal.models.quote import Quote
from investment_terminal.repositories.base_repository import BaseRepository


class QuoteRepository(BaseRepository):
    """
    Persist and retrieve :class:`Quote` records from the SQLite database.
    """

    def __init__(self, database: Database) -> None:
        """
        Create a repository backed by an initialized database.
        """
        self.database = database

    def save(self, model: Quote) -> int:
        """
        Store a quote and return its database identifier.
        """
        self._validate_quote(model)

        cursor = self.database.connection.execute(
            """
            INSERT INTO quotes (symbol, price, currency, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (
                model.symbol,
                float(model.price),
                model.currency,
                model.timestamp.isoformat(),
            ),
        )
        self.database.connection.commit()

        return int(cursor.lastrowid)

    def get(self, quote_id: int) -> Quote | None:
        """
        Return a quote by its identifier, or ``None`` when it does not exist.
        """
        self._validate_quote_id(quote_id)

        row = self.database.connection.execute(
            """
            SELECT symbol, price, currency, timestamp
            FROM quotes
            WHERE id = ?
            """,
            (quote_id,),
        ).fetchone()

        return self._row_to_quote(row) if row is not None else None

    def get_all(self) -> list[Quote]:
        """
        Return all saved quotes ordered by their identifiers.
        """
        rows = self.database.connection.execute(
            """
            SELECT symbol, price, currency, timestamp
            FROM quotes
            ORDER BY id
            """
        ).fetchall()

        return [self._row_to_quote(row) for row in rows]

    def update(self, quote_id: int, model: Quote) -> bool:
        """
        Replace the stored values for a quote.

        Returns ``True`` when a record was updated and ``False`` when the
        identifier does not exist.
        """
        self._validate_quote_id(quote_id)
        self._validate_quote(model)

        cursor = self.database.connection.execute(
            """
            UPDATE quotes
            SET symbol = ?, price = ?, currency = ?, timestamp = ?
            WHERE id = ?
            """,
            (
                model.symbol,
                float(model.price),
                model.currency,
                model.timestamp.isoformat(),
                quote_id,
            ),
        )
        self.database.connection.commit()

        return cursor.rowcount == 1

    def delete(self, quote_id: int) -> bool:
        """
        Delete a quote by its identifier.

        Returns ``True`` when a record was deleted and ``False`` when the
        identifier does not exist.
        """
        self._validate_quote_id(quote_id)

        cursor = self.database.connection.execute(
            "DELETE FROM quotes WHERE id = ?",
            (quote_id,),
        )
        self.database.connection.commit()

        return cursor.rowcount == 1

    @staticmethod
    def _row_to_quote(row) -> Quote:
        """
        Convert a SQLite row into a Quote model.
        """
        return Quote(
            symbol=row["symbol"],
            price=row["price"],
            currency=row["currency"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )

    @staticmethod
    def _validate_quote(model: Quote) -> None:
        """
        Validate values required by the quotes table.
        """
        if not isinstance(model, Quote):
            raise TypeError("model must be a Quote instance")

        if not isinstance(model.symbol, str) or not model.symbol.strip():
            raise ValueError("quote symbol must be a non-empty string")

        if (
            isinstance(model.price, bool)
            or not isinstance(model.price, Real)
            or not isfinite(float(model.price))
        ):
            raise ValueError("quote price must be a finite number")

        if not isinstance(model.currency, str) or not model.currency.strip():
            raise ValueError("quote currency must be a non-empty string")

        if not isinstance(model.timestamp, datetime):
            raise ValueError("quote timestamp must be a datetime")

    @staticmethod
    def _validate_quote_id(quote_id: int) -> None:
        """
        Validate a SQLite primary-key value.
        """
        if isinstance(quote_id, bool) or not isinstance(quote_id, int) or quote_id <= 0:
            raise ValueError("quote_id must be a positive integer")
