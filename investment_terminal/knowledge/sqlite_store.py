"""
SQLite storage owned exclusively by the Knowledge Domain.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path


class KnowledgeSQLiteStore:
    """Own the rebuildable Knowledge Domain SQLite database."""

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
                    INSERT OR IGNORE INTO knowledge_schema_metadata (
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
        with closing(self.connect()) as connection:
            try:
                row = connection.execute(
                    """
                    SELECT value
                    FROM knowledge_schema_metadata
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
        with closing(self.connect()) as connection:
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
        CREATE TABLE IF NOT EXISTS knowledge_schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS knowledge_records (
            knowledge_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            knowledge_type TEXT NOT NULL,
            subject_key TEXT NOT NULL,
            statement TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            generated_at TEXT NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY (
                knowledge_id,
                version
            )
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_records_generated
            ON knowledge_records (
                generated_at,
                knowledge_id,
                version
            );

        CREATE INDEX IF NOT EXISTS idx_knowledge_records_subject_validity
            ON knowledge_records (
                subject_key,
                valid_from,
                generated_at,
                knowledge_id,
                version
            );

        CREATE TABLE IF NOT EXISTS knowledge_evidence (
            knowledge_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            evidence_order INTEGER NOT NULL,
            evidence_type TEXT NOT NULL,
            evidence_id TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            checksum_sha256 TEXT,
            PRIMARY KEY (
                knowledge_id,
                version,
                evidence_order
            ),
            UNIQUE (
                knowledge_id,
                version,
                evidence_type,
                evidence_id
            ),
            FOREIGN KEY (
                knowledge_id,
                version
            )
            REFERENCES knowledge_records (
                knowledge_id,
                version
            )
            ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_evidence_identity
            ON knowledge_evidence (
                evidence_type,
                evidence_id
            );
        """
