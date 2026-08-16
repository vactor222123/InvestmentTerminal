import sqlite3
from pathlib import Path

from investment_terminal.knowledge.sqlite_store import KnowledgeSQLiteStore


def test_short_lived_store_operations_release_sqlite_connection(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    store = KnowledgeSQLiteStore(
        database
    )

    store.initialize()
    assert store.schema_version() == 1
    assert store.table_names() == (
        "knowledge_evidence",
        "knowledge_records",
        "knowledge_schema_metadata",
    )

    # A fresh connection must be able to drain WAL and leave WAL mode
    # immediately. On Windows this fails with "database is locked" if one of
    # the store's short-lived helper connections was only committed but not
    # actually closed.
    connection = sqlite3.connect(
        database
    )
    try:
        checkpoint = connection.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        ).fetchone()
        assert checkpoint is not None
        assert int(checkpoint[0]) == 0

        mode = connection.execute(
            "PRAGMA journal_mode = DELETE"
        ).fetchone()
        assert mode is not None
        assert str(mode[0]).lower() == "delete"
    finally:
        connection.close()
