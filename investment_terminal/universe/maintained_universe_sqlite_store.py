"""SQLite schema and transaction mechanics for maintained universes."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path


class MaintainedAssetUniverseSQLiteStore:
    """Own one durable maintained asset-universe database."""

    SCHEMA_VERSION = 1

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
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
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            with connection:
                connection.executescript(self._schema_sql())
                connection.execute(
                    "INSERT OR IGNORE INTO maintained_universe_metadata "
                    "(key, value) VALUES ('schema_version', ?)",
                    (str(self.SCHEMA_VERSION),),
                )
                row = connection.execute(
                    "SELECT value FROM maintained_universe_metadata "
                    "WHERE key = 'schema_version'"
                ).fetchone()
                if (
                    row is None
                    or row["value"] != str(self.SCHEMA_VERSION)
                ):
                    raise RuntimeError(
                        "maintained universe schema version mismatch"
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
                    "SELECT value FROM maintained_universe_metadata "
                    "WHERE key = 'schema_version'"
                ).fetchone()
            except sqlite3.OperationalError:
                return None
        return int(row["value"]) if row is not None else None

    @staticmethod
    def _schema_sql() -> str:
        return """
        CREATE TABLE IF NOT EXISTS maintained_universe_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maintained_universe_evidence (
            universe_key TEXT PRIMARY KEY,
            universe_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            as_of TEXT NOT NULL,
            source TEXT NOT NULL,
            source_record_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            UNIQUE (source, source_record_key)
        );
        CREATE INDEX IF NOT EXISTS idx_maintained_universe_time
            ON maintained_universe_evidence (
                as_of, universe_id, version, universe_key
            );
        CREATE INDEX IF NOT EXISTS idx_maintained_universe_history
            ON maintained_universe_evidence (
                universe_id, as_of, version, universe_key
            );
        CREATE TABLE IF NOT EXISTS maintained_universe_members (
            universe_key TEXT NOT NULL REFERENCES maintained_universe_evidence
                (universe_key) ON DELETE RESTRICT,
            instrument_key TEXT NOT NULL,
            PRIMARY KEY (universe_key, instrument_key)
        );
        CREATE INDEX IF NOT EXISTS idx_maintained_universe_member
            ON maintained_universe_members (instrument_key, universe_key);
        """
