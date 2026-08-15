"""SQLite storage mechanics for persisted admissible grounded generations."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path


class GroundedGenerationSQLiteStore:
    """Own the durable grounded-generation SQLite schema and transactions."""

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
        with closing(self.connect()) as connection:
            with connection:
                connection.executescript(
                    self._schema_sql()
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO grounded_generation_schema_metadata (
                        key,
                        value
                    )
                    VALUES ('schema_version', ?)
                    """,
                    (str(self.SCHEMA_VERSION),),
                )
        return self.database_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
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
        with closing(self.connect()) as connection:
            try:
                row = connection.execute(
                    """
                    SELECT value
                    FROM grounded_generation_schema_metadata
                    WHERE key = 'schema_version'
                    """
                ).fetchone()
            except sqlite3.OperationalError:
                return None
        if row is None:
            return None
        return int(row["value"])

    @staticmethod
    def _schema_sql() -> str:
        return """
        CREATE TABLE IF NOT EXISTS grounded_generation_schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS grounded_generations (
            request_id TEXT PRIMARY KEY,
            generated_at TEXT NOT NULL,
            prompt_protocol_identity TEXT NOT NULL,
            answer_protocol_identity TEXT NOT NULL,
            provider_identity TEXT NOT NULL,
            model_identity TEXT NOT NULL,
            selected_knowledge_identities_json TEXT NOT NULL,
            cited_knowledge_identities_json TEXT NOT NULL,
            generation_json TEXT NOT NULL,
            trace_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_grounded_generations_generated
            ON grounded_generations (
                generated_at,
                request_id
            );
        """
