"""
Tests for the SQLite structured history store.
"""

import sqlite3
from pathlib import Path

import pytest

from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


EXPECTED_TABLES = (
    "deployment",
    "holdings",
    "portfolio_summary",
    "recommendations",
    "schema_metadata",
    "snapshots",
    "timeline_events",
)


def test_store_initializes_expected_schema(
    tmp_path: Path,
) -> None:
    database = (
        tmp_path
        / "history"
        / "history.db"
    )
    store = HistoricalSQLiteStore(
        database
    )

    result = store.initialize()

    assert result == database
    assert database.exists()
    assert store.schema_version() == 1
    assert store.table_names() == (
        EXPECTED_TABLES
    )


def test_initialization_is_idempotent(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )

    store.initialize()
    store.initialize()

    assert store.schema_version() == 1
    assert store.table_names() == (
        EXPECTED_TABLES
    )


def test_store_enables_foreign_keys(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    store.initialize()

    with store.connect() as connection:
        enabled = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

    assert enabled == 1


def test_store_rejects_orphan_portfolio_summary(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    store.initialize()

    with store.connect() as connection:
        with pytest.raises(
            sqlite3.IntegrityError,
        ):
            connection.execute(
                """
                INSERT INTO portfolio_summary (
                    snapshot_id,
                    portfolio_name
                )
                VALUES (
                    'missing-snapshot',
                    'Portfolio'
                )
                """
            )


def test_store_rejects_duplicate_archive_path(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    store.initialize()

    values = (
        "snapshot-1",
        "1.0",
        "2026-08-03T17:35:00+00:00",
        "2026-08-03T17:36:00+00:00",
        "2026/08/review.json",
        "a" * 64,
        "ARCHIVED",
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO snapshots (
                snapshot_id,
                package_schema_version,
                generated_at,
                archived_at,
                relative_path,
                checksum_sha256,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )

        with pytest.raises(
            sqlite3.IntegrityError,
        ):
            connection.execute(
                """
                INSERT INTO snapshots (
                    snapshot_id,
                    package_schema_version,
                    generated_at,
                    archived_at,
                    relative_path,
                    checksum_sha256,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "snapshot-2",
                    *values[1:],
                ),
            )


def test_schema_version_is_none_before_initialization(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )

    assert store.schema_version() is None


@pytest.mark.parametrize(
    "database_name",
    (
        "history.json",
        "history.txt",
        "history",
    ),
)
def test_store_rejects_invalid_extension(
    tmp_path: Path,
    database_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "database_path must use "
            ".db, .sqlite, or .sqlite3"
        ),
    ):
        HistoricalSQLiteStore(
            tmp_path / database_name
        )
