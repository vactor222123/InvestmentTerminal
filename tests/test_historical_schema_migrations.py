"""
Tests for History SQLite schema migration primitives.
"""

import sqlite3
from pathlib import Path

import pytest

from investment_terminal.history.historical_schema_migrations import (
    HistoricalSchemaMigration,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


def create_store(
    tmp_path: Path,
) -> HistoricalSQLiteStore:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    store.initialize()
    return store


def migration_1_to_2() -> HistoricalSchemaMigration:
    return HistoricalSchemaMigration(
        from_version=1,
        to_version=2,
        name="add migration marker",
        statements=(
            """
            CREATE TABLE migration_marker (
                marker TEXT PRIMARY KEY
            )
            """,
        ),
    )


def migration_2_to_3() -> HistoricalSchemaMigration:
    return HistoricalSchemaMigration(
        from_version=2,
        to_version=3,
        name="extend migration marker",
        statements=(
            """
            ALTER TABLE migration_marker
            ADD COLUMN note TEXT
            """,
        ),
    )


def test_migration_validates_forward_single_step() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "to_version must be exactly one greater than from_version"
        ),
    ):
        HistoricalSchemaMigration(
            from_version=1,
            to_version=3,
            name="invalid jump",
            statements=(
                "SELECT 1",
            ),
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "from_version",
        "to_version",
    ),
)
def test_migration_rejects_invalid_versions(
    field_name: str,
) -> None:
    values = {
        "from_version": 1,
        "to_version": 2,
    }
    values[
        field_name
    ] = 0

    with pytest.raises(
        ValueError,
        match=(
            f"{field_name} must be a positive integer"
        ),
    ):
        HistoricalSchemaMigration(
            **values,
            name="invalid",
            statements=(
                "SELECT 1",
            ),
        )


def test_migration_rejects_empty_statement_set() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "statements must contain at least one SQL statement"
        ),
    ):
        HistoricalSchemaMigration(
            from_version=1,
            to_version=2,
            name="empty",
            statements=(),
        )


def test_migrator_requires_initialized_schema(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    migrator = HistoricalSchemaMigrator(
        store=store,
        migrations=(
            migration_1_to_2(),
        ),
        target_version=2,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "History schema must be initialized before migration"
        ),
    ):
        migrator.migrate()


def test_migrator_applies_sequential_migrations(
    tmp_path: Path,
) -> None:
    store = create_store(
        tmp_path
    )
    migrator = HistoricalSchemaMigrator(
        store=store,
        migrations=(
            migration_2_to_3(),
            migration_1_to_2(),
        ),
        target_version=3,
    )

    assert migrator.migrate() == 3
    assert store.schema_version() == 3

    with store.connect() as connection:
        columns = connection.execute(
            """
            PRAGMA table_info(migration_marker)
            """
        ).fetchall()

    assert tuple(
        row["name"]
        for row in columns
    ) == (
        "marker",
        "note",
    )


def test_migrator_is_idempotent_at_target_version(
    tmp_path: Path,
) -> None:
    store = create_store(
        tmp_path
    )
    migrator = HistoricalSchemaMigrator(
        store=store,
        migrations=(
            migration_1_to_2(),
        ),
        target_version=2,
    )

    assert migrator.migrate() == 2
    assert migrator.migrate() == 2
    assert store.schema_version() == 2


def test_migrator_rejects_unsupported_future_schema(
    tmp_path: Path,
) -> None:
    store = create_store(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            UPDATE schema_metadata
            SET value = '4'
            WHERE key = 'schema_version'
            """
        )

    migrator = HistoricalSchemaMigrator(
        store=store,
        migrations=(
            migration_1_to_2(),
        ),
        target_version=2,
    )

    with pytest.raises(
        RuntimeError,
        match="newer than supported target version 2",
    ):
        migrator.migrate()

    assert store.schema_version() == 4


def test_migrator_rejects_missing_migration_step(
    tmp_path: Path,
) -> None:
    store = create_store(
        tmp_path
    )
    migrator = HistoricalSchemaMigrator(
        store=store,
        migrations=(
            migration_2_to_3(),
        ),
        target_version=3,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "No History schema migration is registered from version 1"
        ),
    ):
        migrator.migrate()

    assert store.schema_version() == 1


def test_migrator_rolls_back_complete_upgrade_on_failure(
    tmp_path: Path,
) -> None:
    store = create_store(
        tmp_path
    )
    first = migration_1_to_2()
    failing = HistoricalSchemaMigration(
        from_version=2,
        to_version=3,
        name="failing migration",
        statements=(
            """
            CREATE TABLE should_roll_back (
                id INTEGER PRIMARY KEY
            )
            """,
            """
            CREATE TABLE migration_marker (
                duplicate INTEGER
            )
            """,
        ),
    )
    migrator = HistoricalSchemaMigrator(
        store=store,
        migrations=(
            first,
            failing,
        ),
        target_version=3,
    )

    with pytest.raises(
        sqlite3.OperationalError,
    ):
        migrator.migrate()

    assert store.schema_version() == 1
    assert "migration_marker" not in store.table_names()
    assert "should_roll_back" not in store.table_names()


def test_migrator_rolls_back_on_base_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = create_store(
        tmp_path
    )
    migration = migration_1_to_2()

    class SimulatedInterruption(
        BaseException
    ):
        pass

    original_apply = HistoricalSchemaMigration.apply

    def interrupted_apply(
        self,
        connection,
    ) -> None:
        original_apply(
            self,
            connection,
        )
        raise SimulatedInterruption()

    monkeypatch.setattr(
        HistoricalSchemaMigration,
        "apply",
        interrupted_apply,
    )

    migrator = HistoricalSchemaMigrator(
        store=store,
        migrations=(
            migration,
        ),
        target_version=2,
    )

    with pytest.raises(
        SimulatedInterruption,
    ):
        migrator.migrate()

    assert store.schema_version() == 1
    assert "migration_marker" not in store.table_names()


def test_migrator_rejects_duplicate_from_versions(
    tmp_path: Path,
) -> None:
    store = create_store(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match=(
            "migrations must not contain duplicate from_version values"
        ),
    ):
        HistoricalSchemaMigrator(
            store=store,
            migrations=(
                migration_1_to_2(),
                HistoricalSchemaMigration(
                    from_version=1,
                    to_version=2,
                    name="duplicate",
                    statements=(
                        "CREATE TABLE other_marker (id INTEGER)",
                    ),
                ),
            ),
            target_version=2,
        )


def test_migrator_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match="store must be a HistoricalSQLiteStore",
    ):
        HistoricalSchemaMigrator(
            store=object(),  # type: ignore[arg-type]
            migrations=(),
            target_version=1,
        )
