"""SQLite schema and transaction mechanics for portfolio transactions."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from investment_terminal.portfolio.transaction_ledger_models import (
    PortfolioTransactionLedger,
)


class PortfolioTransactionSQLiteStore:
    """Own one durable portfolio transaction-ledger database."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        database_path: str | Path,
        *,
        ledger_id: str,
        portfolio_name: str,
        base_currency: str,
    ) -> None:
        self.database_path = Path(database_path)
        if (
            self.database_path.name != ":memory:"
            and self.database_path.suffix.lower()
            not in {".db", ".sqlite", ".sqlite3"}
        ):
            raise ValueError(
                "database_path must use .db, .sqlite, or .sqlite3"
            )
        metadata = PortfolioTransactionLedger(
            ledger_id=ledger_id,
            portfolio_name=portfolio_name,
            base_currency=base_currency,
            transactions=(),
        )
        self.ledger_id = metadata.ledger_id
        self.portfolio_name = metadata.portfolio_name
        self.base_currency = metadata.base_currency

    def initialize(self) -> Path:
        if self.database_path.name != ":memory:":
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            with connection:
                connection.executescript(self._schema_sql())
                values = {
                    "schema_version": str(self.SCHEMA_VERSION),
                    "ledger_id": self.ledger_id,
                    "portfolio_name": self.portfolio_name,
                    "base_currency": self.base_currency,
                }
                connection.executemany(
                    "INSERT OR IGNORE INTO portfolio_transaction_metadata "
                    "(key, value) VALUES (?, ?)",
                    tuple(values.items()),
                )
                rows = connection.execute(
                    "SELECT key, value FROM portfolio_transaction_metadata"
                ).fetchall()
                actual = {row["key"]: row["value"] for row in rows}
                if actual != values:
                    raise RuntimeError(
                        "transaction database metadata does not match store configuration"
                    )
        return self.database_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.initialize()
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
        except BaseException:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def schema_version(self) -> int | None:
        with closing(self.connect()) as connection:
            try:
                row = connection.execute(
                    "SELECT value FROM portfolio_transaction_metadata "
                    "WHERE key = 'schema_version'"
                ).fetchone()
            except sqlite3.OperationalError:
                return None
        return int(row["value"]) if row is not None else None

    @staticmethod
    def _schema_sql() -> str:
        return """
        CREATE TABLE IF NOT EXISTS portfolio_transaction_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            transaction_id TEXT PRIMARY KEY,
            occurred_at TEXT NOT NULL,
            instrument_key TEXT,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_time
            ON portfolio_transactions (occurred_at, transaction_id);
        CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_instrument
            ON portfolio_transactions (
                instrument_key, occurred_at, transaction_id
            );
        """
