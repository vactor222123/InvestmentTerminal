"""SQLite schema and transaction mechanics for valuation history."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from investment_terminal.portfolio.portfolio_valuation_history import (
    PortfolioValuationHistory,
)


class PortfolioValuationHistorySQLiteStore:
    """Own one durable portfolio valuation-history database."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        database_path: str | Path,
        *,
        ledger_id: str,
        portfolio_name: str,
    ) -> None:
        self.database_path = Path(database_path)
        if (
            self.database_path.name != ":memory:"
            and self.database_path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}
        ):
            raise ValueError("database_path must use .db, .sqlite, or .sqlite3")
        metadata = PortfolioValuationHistory(
            ledger_id=ledger_id,
            portfolio_name=portfolio_name,
            snapshots=(),
        )
        self.ledger_id = metadata.ledger_id
        self.portfolio_name = metadata.portfolio_name

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
                }
                connection.executemany(
                    "INSERT OR IGNORE INTO portfolio_valuation_metadata "
                    "(key, value) VALUES (?, ?)",
                    tuple(values.items()),
                )
                rows = connection.execute(
                    "SELECT key, value FROM portfolio_valuation_metadata"
                ).fetchall()
                actual = {row["key"]: row["value"] for row in rows}
                if actual != values:
                    raise RuntimeError(
                        "valuation database metadata does not match store configuration"
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
                    "SELECT value FROM portfolio_valuation_metadata "
                    "WHERE key = 'schema_version'"
                ).fetchone()
            except sqlite3.OperationalError:
                return None
        return int(row["value"]) if row is not None else None

    @staticmethod
    def _schema_sql() -> str:
        return """
        CREATE TABLE IF NOT EXISTS portfolio_valuation_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS portfolio_valuation_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            valued_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_portfolio_valuation_snapshots_time
            ON portfolio_valuation_snapshots (valued_at, snapshot_id);
        """
