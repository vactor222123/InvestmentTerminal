"""
Tests for the production History schema v1-to-v2 migration.
"""

import sqlite3
from pathlib import Path

import pytest

from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


def create_v1_store(
    tmp_path: Path,
) -> HistoricalSQLiteStore:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    store.initialize()
    assert store.schema_version() == 1
    return store


def migrate_to_v2(
    store: HistoricalSQLiteStore,
) -> int:
    return HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()


def test_production_migration_upgrades_v1_to_v2(
    tmp_path: Path,
) -> None:
    store = create_v1_store(
        tmp_path
    )

    assert migrate_to_v2(
        store
    ) == 2
    assert store.schema_version() == 2
    assert "historical_import_state" in store.table_names()


def test_production_migration_preserves_existing_snapshots(
    tmp_path: Path,
) -> None:
    store = create_v1_store(
        tmp_path
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
            (
                "snapshot-existing",
                "1.0",
                "2026-08-03T17:35:00+00:00",
                "2026-08-03T17:36:00+00:00",
                "2026/08/existing.json",
                "a" * 64,
                "ARCHIVED",
            ),
        )

    migrate_to_v2(
        store
    )

    with store.connect() as connection:
        row = connection.execute(
            """
            SELECT snapshot_id
            FROM snapshots
            WHERE snapshot_id = 'snapshot-existing'
            """
        ).fetchone()

    assert row is not None
    assert row["snapshot_id"] == "snapshot-existing"


def test_import_state_table_enforces_snapshot_foreign_key(
    tmp_path: Path,
) -> None:
    store = create_v1_store(
        tmp_path
    )
    migrate_to_v2(
        store
    )

    with pytest.raises(
        sqlite3.IntegrityError,
    ):
        with store.connect() as connection:
            connection.execute(
                """
                INSERT INTO historical_import_state (
                    snapshot_id,
                    status,
                    metadata_synchronized_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    "missing-snapshot",
                    "METADATA_ONLY",
                    "2026-08-08T10:00:00+00:00",
                    "2026-08-08T10:00:00+00:00",
                ),
            )


def test_import_state_table_enforces_status_constraint(
    tmp_path: Path,
) -> None:
    store = create_v1_store(
        tmp_path
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

    migrate_to_v2(
        store
    )

    with pytest.raises(
        sqlite3.IntegrityError,
    ):
        with store.connect() as connection:
            connection.execute(
                """
                INSERT INTO historical_import_state (
                    snapshot_id,
                    status,
                    metadata_synchronized_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    "snapshot-1",
                    "UNKNOWN",
                    "2026-08-08T10:00:00+00:00",
                    "2026-08-08T10:00:00+00:00",
                ),
            )


def test_production_migration_is_idempotent(
    tmp_path: Path,
) -> None:
    store = create_v1_store(
        tmp_path
    )

    assert migrate_to_v2(
        store
    ) == 2
    assert migrate_to_v2(
        store
    ) == 2
    assert store.schema_version() == 2
