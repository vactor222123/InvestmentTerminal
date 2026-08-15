"""
SQLite storage for the provider usage/cost ledger.

This store owns only durable ledger schema and transaction mechanics. Repository
semantics and record mapping remain separate.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class GroundedProviderUsageCostLedgerSQLiteStore:
    """Own the durable provider usage/cost ledger SQLite database."""

    SCHEMA_VERSION = 1

    def __init__(
        self,
        database_path: str | Path,
    ) -> None:
        self.database_path = (
            database_path
            if isinstance(database_path, Path)
            else Path(database_path)
        )

        if (
            self.database_path.name != ":memory:"
            and self.database_path.suffix.lower()
            not in {".db", ".sqlite", ".sqlite3"}
        ):
            raise ValueError(
                "database_path must use .db, .sqlite, or .sqlite3"
            )

    def initialize(self) -> Path:
        if self.database_path.name != ":memory:":
            self.database_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        with self.connect() as connection:
            connection.executescript(
                self._schema_sql()
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO provider_usage_cost_schema_metadata (
                    key,
                    value
                )
                VALUES (
                    'schema_version',
                    ?
                )
                """,
                (
                    str(self.SCHEMA_VERSION),
                ),
            )

        return self.database_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path
        )
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
        connection.execute(
            "PRAGMA synchronous = NORMAL"
        )
        return connection

    @contextmanager
    def transaction(
        self,
    ) -> Iterator[sqlite3.Connection]:
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
        with self.connect() as connection:
            try:
                row = connection.execute(
                    """
                    SELECT value
                    FROM provider_usage_cost_schema_metadata
                    WHERE key = 'schema_version'
                    """
                ).fetchone()
            except sqlite3.OperationalError:
                return None

        if row is None:
            return None
        return int(
            row["value"]
        )

    def table_names(self) -> tuple[str, ...]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()

        return tuple(
            row["name"]
            for row in rows
        )

    @staticmethod
    def _schema_sql() -> str:
        return """
        CREATE TABLE IF NOT EXISTS provider_usage_cost_schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS provider_usage_cost_ledger (
            request_id TEXT PRIMARY KEY,
            provider_identity TEXT NOT NULL,
            model_identity TEXT NOT NULL,
            input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
            output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
            total_tokens INTEGER NOT NULL CHECK (
                total_tokens >= 0
                AND total_tokens = input_tokens + output_tokens
            ),
            currency TEXT NOT NULL,
            input_cost TEXT NOT NULL,
            output_cost TEXT NOT NULL,
            total_cost TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_provider_usage_cost_recorded
            ON provider_usage_cost_ledger (
                recorded_at,
                request_id
            );

        CREATE INDEX IF NOT EXISTS idx_provider_usage_cost_provider_model
            ON provider_usage_cost_ledger (
                provider_identity,
                model_identity,
                recorded_at,
                request_id
            );
        """

