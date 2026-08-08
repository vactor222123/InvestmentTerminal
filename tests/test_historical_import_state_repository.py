"""
Tests for HistoricalImportStateRepository.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
BASE_TIME = datetime(
    2026,
    8,
    8,
    10,
    0,
    tzinfo=timezone.utc,
)


def create_snapshot() -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.13.0",
        generated_at=BASE_TIME - timedelta(
            minutes=2
        ),
        archived_at=BASE_TIME - timedelta(
            minutes=1
        ),
        relative_path=(
            f"2026/08/{SNAPSHOT_ID}.json"
        ),
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )


def create_repository(
    tmp_path: Path,
) -> tuple[
    HistoricalSnapshot,
    HistoricalImportStateRepository,
]:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    snapshot = create_snapshot()
    HistoricalSnapshotRepository(
        store
    ).add(
        snapshot
    )
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    return (
        snapshot,
        HistoricalImportStateRepository(
            store
        ),
    )


def test_repository_rejects_invalid_store() -> None:
    with pytest.raises(
        TypeError,
        match="store must be a HistoricalSQLiteStore",
    ):
        HistoricalImportStateRepository(
            object()  # type: ignore[arg-type]
        )


def test_repository_get_returns_none_when_absent(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )

    assert repository.get(
        SNAPSHOT_ID
    ) is None

    with pytest.raises(
        KeyError,
        match="No historical import state found",
    ):
        repository.require(
            SNAPSHOT_ID
        )


def test_repository_initializes_metadata_state(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )

    state = repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )

    assert state.status == "METADATA_ONLY"
    assert repository.require(
        SNAPSHOT_ID.upper()
    ) == state


def test_repository_rejects_duplicate_metadata_state(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )
    repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )

    with pytest.raises(
        ValueError,
        match="Historical import state already exists",
    ):
        repository.initialize_metadata(
            snapshot,
            at=BASE_TIME,
        )


def test_repository_rejects_unregistered_snapshot(
    tmp_path: Path,
) -> None:
    _, repository = create_repository(
        tmp_path
    )
    other = HistoricalSnapshot(
        snapshot_id=(
            "f9b7adca-2f2b-47a4-901d-05ca37c445df"
        ),
        package_schema_version="1.0",
        generated_at=BASE_TIME,
        archived_at=BASE_TIME,
        relative_path=(
            "2026/08/"
            "f9b7adca-2f2b-47a4-901d-05ca37c445df.json"
        ),
        checksum_sha256="b" * 64,
        status="ARCHIVED",
    )

    with pytest.raises(
        ValueError,
        match="references an unknown snapshot",
    ):
        repository.initialize_metadata(
            other,
            at=BASE_TIME,
        )


def test_repository_persists_complete_successful_lifecycle(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )
    repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )

    verified = repository.mark_verified(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=1
        ),
    )
    importing = repository.mark_importing(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=2
        ),
        importer_version="0.13.0",
    )
    imported = repository.mark_imported(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=3
        ),
    )

    assert verified.status == "VERIFIED"
    assert importing.status == "IMPORTING"
    assert importing.importer_version == "0.13.0"
    assert imported.status == "IMPORTED"
    assert imported.package_verified_at == (
        BASE_TIME + timedelta(
            minutes=1
        )
    )
    assert imported.details_imported_at == (
        BASE_TIME + timedelta(
            minutes=3
        )
    )
    assert imported.timeline_built_at == (
        BASE_TIME + timedelta(
            minutes=3
        )
    )
    assert repository.require(
        SNAPSHOT_ID
    ) == imported


def test_repository_persists_failure_and_retry(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )
    repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )

    failed = repository.mark_failed(
        SNAPSHOT_ID,
        reason=" checksum mismatch ",
        at=BASE_TIME + timedelta(
            minutes=1
        ),
    )

    assert failed.status == "FAILED"
    assert failed.failure_reason == "checksum mismatch"

    retried = repository.mark_verified(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=2
        ),
    )

    assert retried.status == "VERIFIED"
    assert retried.failure_reason is None
    assert retried.package_verified_at == (
        BASE_TIME + timedelta(
            minutes=2
        )
    )


def test_repository_rejects_invalid_transition(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )
    repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )

    with pytest.raises(
        ValueError,
        match="METADATA_ONLY -> IMPORTED",
    ):
        repository.mark_imported(
            SNAPSHOT_ID,
            at=BASE_TIME + timedelta(
                minutes=1
            ),
        )


def test_repository_rejects_time_regression(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )
    repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )
    repository.mark_verified(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=2
        ),
    )

    with pytest.raises(
        ValueError,
        match="at must not be earlier than the current updated_at",
    ):
        repository.mark_importing(
            SNAPSHOT_ID,
            at=BASE_TIME + timedelta(
                minutes=1
            ),
        )


def test_repository_rejects_naive_transition_time(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )
    repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )

    with pytest.raises(
        ValueError,
        match="at must be timezone-aware",
    ):
        repository.mark_verified(
            SNAPSHOT_ID,
            at=datetime(
                2026,
                8,
                8,
                11,
                0,
            ),
        )


def test_imported_state_is_terminal(
    tmp_path: Path,
) -> None:
    snapshot, repository = create_repository(
        tmp_path
    )
    repository.initialize_metadata(
        snapshot,
        at=BASE_TIME,
    )
    repository.mark_verified(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=1
        ),
    )
    repository.mark_importing(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=2
        ),
    )
    repository.mark_imported(
        SNAPSHOT_ID,
        at=BASE_TIME + timedelta(
            minutes=3
        ),
    )

    with pytest.raises(
        ValueError,
        match="IMPORTED -> FAILED",
    ):
        repository.mark_failed(
            SNAPSHOT_ID,
            reason="late failure",
            at=BASE_TIME + timedelta(
                minutes=4
            ),
        )


def test_repository_requires_explicit_v2_migration(
    tmp_path: Path,
) -> None:
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    store.initialize()
    repository = HistoricalImportStateRepository(
        store
    )

    with pytest.raises(
        RuntimeError,
        match="requires History schema version 2",
    ):
        repository.get(
            SNAPSHOT_ID
        )
