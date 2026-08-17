"""SQLite storage mechanics for external context."""
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

class ExternalContextSQLiteStore:
    SCHEMA_VERSION = 1
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        if self.database_path.name != ":memory:" and self.database_path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            raise ValueError("database_path must use .db, .sqlite, or .sqlite3")
    def initialize(self) -> Path:
        if self.database_path.name != ":memory:": self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            with connection:
                connection.executescript(self._schema_sql())
                connection.execute("INSERT OR IGNORE INTO external_context_metadata (key,value) VALUES ('schema_version',?)", (str(self.SCHEMA_VERSION),))
                row = connection.execute("SELECT value FROM external_context_metadata WHERE key='schema_version'").fetchone()
                if row is None or row["value"] != str(self.SCHEMA_VERSION): raise RuntimeError("external context schema version mismatch")
        return self.database_path
    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path); connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON"); connection.execute("PRAGMA journal_mode = WAL"); return connection
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.initialize(); connection = self.connect()
        try:
            connection.execute("BEGIN"); yield connection
        except BaseException:
            connection.rollback(); raise
        else: connection.commit()
        finally: connection.close()
    @staticmethod
    def _schema_sql() -> str:
        return """CREATE TABLE IF NOT EXISTS external_context_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS external_context_evidence(context_id TEXT PRIMARY KEY,source TEXT NOT NULL,source_record_id TEXT NOT NULL,published_at TEXT NOT NULL,payload_json TEXT NOT NULL,UNIQUE(source,source_record_id)); CREATE INDEX IF NOT EXISTS idx_external_context_time ON external_context_evidence(published_at,context_id); CREATE TABLE IF NOT EXISTS external_context_subjects(context_id TEXT NOT NULL REFERENCES external_context_evidence(context_id) ON DELETE RESTRICT,subject_key TEXT NOT NULL,PRIMARY KEY(context_id,subject_key)); CREATE INDEX IF NOT EXISTS idx_external_context_subject ON external_context_subjects(subject_key,context_id);"""
