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


def test_transaction_commits_successful_work(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )

    with store.transaction() as connection:
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
                "snapshot-1",
                "1.0",
                "2026-08-03T17:35:00+00:00",
                "2026-08-03T17:36:00+00:00",
                "2026/08/review.json",
                "a" * 64,
                "ARCHIVED",
            ),
        )

    with store.connect() as connection:
        row = connection.execute(
            """
            SELECT snapshot_id
            FROM snapshots
            """
        ).fetchone()

    assert row["snapshot_id"] == "snapshot-1"


def test_transaction_rolls_back_all_work_on_failure(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )

    with pytest.raises(
        RuntimeError,
        match="import failed",
    ):
        with store.transaction() as connection:
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
                    "snapshot-1",
                    "1.0",
                    "2026-08-03T17:35:00+00:00",
                    "2026-08-03T17:36:00+00:00",
                    "2026/08/review.json",
                    "a" * 64,
                    "ARCHIVED",
                ),
            )
            connection.execute(
                """
                INSERT INTO portfolio_summary (
                    snapshot_id,
                    portfolio_name
                )
                VALUES (?, ?)
                """,
                (
                    "snapshot-1",
                    "Portfolio",
                ),
            )
            raise RuntimeError(
                "import failed"
            )

    with store.connect() as connection:
        snapshot_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM snapshots
            """
        ).fetchone()[0]
        summary_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM portfolio_summary
            """
        ).fetchone()[0]

    assert snapshot_count == 0
    assert summary_count == 0


def test_transaction_closes_connection_after_success(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )

    with store.transaction() as connection:
        connection.execute(
            "SELECT 1"
        )

    with pytest.raises(
        sqlite3.ProgrammingError,
        match="closed database",
    ):
        connection.execute(
            "SELECT 1"
        )


def test_transaction_closes_connection_after_failure(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    connection: sqlite3.Connection | None = None

    with pytest.raises(
        RuntimeError,
        match="failed",
    ):
        with store.transaction() as active_connection:
            connection = active_connection
            raise RuntimeError(
                "failed"
            )

    assert connection is not None

    with pytest.raises(
        sqlite3.ProgrammingError,
        match="closed database",
    ):
        connection.execute(
            "SELECT 1"
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
