"""
SQLite schema and connection management for structured history.
"""

import sqlite3
from pathlib import Path


class HistoricalSQLiteStore:
    """
    Own the canonical structured History Domain database.

    Immutable archived Review Packages remain the historical source of truth.
    SQLite is a normalized query and analytics representation.
    """

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
            not in {
                ".db",
                ".sqlite",
                ".sqlite3",
            }
        ):
            raise ValueError(
                "database_path must use .db, .sqlite, or .sqlite3"
            )

    def initialize(
        self,
    ) -> Path:
        """Create the History schema when it does not already exist."""
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
                INSERT OR IGNORE INTO schema_metadata (
                    key,
                    value
                )
                VALUES (
                    'schema_version',
                    ?
                )
                """,
                (
                    str(
                        self.SCHEMA_VERSION
                    ),
                ),
            )

        return self.database_path

    def connect(
        self,
    ) -> sqlite3.Connection:
        """
        Open a configured SQLite connection owned by the History Domain.
        """
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

    def schema_version(
        self,
    ) -> int | None:
        """Return the initialized schema version, or None if absent."""
        with self.connect() as connection:
            try:
                row = connection.execute(
                    """
                    SELECT value
                    FROM schema_metadata
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

    def table_names(
        self,
    ) -> tuple[str, ...]:
        """Return user-owned database tables in alphabetical order."""
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
        CREATE TABLE IF NOT EXISTS schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            package_id TEXT,
            package_schema_version TEXT NOT NULL,
            product_version TEXT,
            generated_at TEXT NOT NULL,
            archived_at TEXT NOT NULL,
            relative_path TEXT NOT NULL UNIQUE,
            checksum_sha256 TEXT NOT NULL,
            supersedes TEXT,
            status TEXT NOT NULL,
            imported_at TEXT,
            FOREIGN KEY (
                supersedes
            )
            REFERENCES snapshots (
                snapshot_id
            )
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_generated_at
            ON snapshots (
                generated_at
            );

        CREATE INDEX IF NOT EXISTS idx_snapshots_package_id
            ON snapshots (
                package_id
            );

        CREATE TABLE IF NOT EXISTS portfolio_summary (
            snapshot_id TEXT PRIMARY KEY,
            portfolio_name TEXT,
            base_currency TEXT,
            total_value REAL,
            invested_value REAL,
            cash_value REAL,
            monthly_contribution REAL,
            source_status TEXT,
            FOREIGN KEY (
                snapshot_id
            )
            REFERENCES snapshots (
                snapshot_id
            )
            ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS holdings (
            snapshot_id TEXT NOT NULL,
            holding_key TEXT NOT NULL,
            symbol TEXT,
            name TEXT,
            asset_type TEXT,
            sleeve TEXT,
            strategy TEXT,
            currency TEXT,
            quantity REAL,
            unit_price REAL,
            market_value REAL,
            weight REAL,
            PRIMARY KEY (
                snapshot_id,
                holding_key
            ),
            FOREIGN KEY (
                snapshot_id
            )
            REFERENCES snapshots (
                snapshot_id
            )
            ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_holdings_symbol
            ON holdings (
                symbol
            );

        CREATE TABLE IF NOT EXISTS recommendations (
            snapshot_id TEXT NOT NULL,
            recommendation_key TEXT NOT NULL,
            symbol TEXT,
            action TEXT,
            score REAL,
            confidence REAL,
            rationale TEXT,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (
                snapshot_id,
                recommendation_key
            ),
            FOREIGN KEY (
                snapshot_id
            )
            REFERENCES snapshots (
                snapshot_id
            )
            ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_recommendations_symbol_action
            ON recommendations (
                symbol,
                action
            );

        CREATE TABLE IF NOT EXISTS deployment (
            snapshot_id TEXT NOT NULL,
            deployment_key TEXT NOT NULL,
            amount REAL,
            share REAL,
            reason TEXT,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (
                snapshot_id,
                deployment_key
            ),
            FOREIGN KEY (
                snapshot_id
            )
            REFERENCES snapshots (
                snapshot_id
            )
            ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS timeline_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            subject_key TEXT,
            payload_json TEXT NOT NULL,
            FOREIGN KEY (
                snapshot_id
            )
            REFERENCES snapshots (
                snapshot_id
            )
            ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_timeline_events_occurred_at
            ON timeline_events (
                occurred_at
            );

        CREATE INDEX IF NOT EXISTS idx_timeline_events_type
            ON timeline_events (
                event_type
            );
        """
