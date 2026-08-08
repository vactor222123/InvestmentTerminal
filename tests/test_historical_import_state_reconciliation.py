"""
Tests for legacy import-state reconciliation.
"""

from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
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
GENERATED_AT = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)
ARCHIVED_AT = datetime(
    2026,
    8,
    3,
    17,
    36,
    tzinfo=timezone.utc,
)
RECONCILED_AT = datetime(
    2026,
    8,
    8,
    14,
    0,
    tzinfo=timezone.utc,
)


def snapshot() -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=GENERATED_AT,
        archived_at=ARCHIVED_AT,
        relative_path=f"2026/08/{SNAPSHOT_ID}.json",
        checksum_sha256="a" * 64,
        status="ARCHIVED",
    )


def create_legacy_store(
    tmp_path: Path,
):
    store = HistoricalSQLiteStore(
        tmp_path / "history.db"
    )
    repository = HistoricalSnapshotRepository(
        store
    )
    item = snapshot()
    repository.add(
        item
    )
    return store, repository, item


def insert_complete_legacy_projection(
    store: HistoricalSQLiteStore,
    item: HistoricalSnapshot,
) -> None:
    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id
            )
            VALUES (?)
            """,
            (
                item.snapshot_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO timeline_events (
                snapshot_id,
                event_type,
                occurred_at,
                subject_key,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item.snapshot_id,
                "SNAPSHOT_ARCHIVED",
                item.archived_at.isoformat(),
                item.snapshot_id,
                "{}",
            ),
        )
        connection.execute(
            """
            INSERT INTO timeline_events (
                snapshot_id,
                event_type,
                occurred_at,
                subject_key,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item.snapshot_id,
                "PORTFOLIO_SUMMARY_RECORDED",
                item.generated_at.isoformat(),
                "Legacy",
                "{}",
            ),
        )


def migrate(
    store: HistoricalSQLiteStore,
) -> None:
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()


def test_complete_legacy_projection_is_detected(
    tmp_path: Path,
) -> None:
    store, repository, item = create_legacy_store(
        tmp_path
    )
    insert_complete_legacy_projection(
        store,
        item,
    )

    assert repository.has_complete_detail_import(
        item.snapshot_id
    )


def test_partial_legacy_projection_is_not_complete(
    tmp_path: Path,
) -> None:
    store, repository, item = create_legacy_store(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id
            )
            VALUES (?)
            """,
            (
                item.snapshot_id,
            ),
        )

    assert not repository.has_complete_detail_import(
        item.snapshot_id
    )


def test_manifest_sync_backfills_imported_for_complete_legacy_projection(
    tmp_path: Path,
) -> None:
    store, repository, item = create_legacy_store(
        tmp_path
    )
    insert_complete_legacy_projection(
        store,
        item,
    )
    migrate(
        store
    )

    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    manifest.append(
        item
    )
    states = HistoricalImportStateRepository(
        store
    )

    HistoricalManifestImportService(
        manifest=manifest,
        repository=repository,
        state_repository=states,
        clock=lambda: RECONCILED_AT,
    ).synchronize()

    state = states.require(
        item.snapshot_id
    )
    assert state.status == "IMPORTED"
    assert state.metadata_synchronized_at == RECONCILED_AT
    assert state.package_verified_at == RECONCILED_AT
    assert state.details_imported_at == RECONCILED_AT
    assert state.timeline_built_at == RECONCILED_AT
    assert state.importer_version == item.product_version


def test_manifest_sync_keeps_partial_legacy_projection_metadata_only(
    tmp_path: Path,
) -> None:
    store, repository, item = create_legacy_store(
        tmp_path
    )

    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO portfolio_summary (
                snapshot_id
            )
            VALUES (?)
            """,
            (
                item.snapshot_id,
            ),
        )

    migrate(
        store
    )

    manifest = HistoricalSnapshotManifest(
        tmp_path / "manifest.jsonl"
    )
    manifest.append(
        item
    )
    states = HistoricalImportStateRepository(
        store
    )

    HistoricalManifestImportService(
        manifest=manifest,
        repository=repository,
        state_repository=states,
        clock=lambda: RECONCILED_AT,
    ).synchronize()

    assert states.require(
        item.snapshot_id
    ).status == "METADATA_ONLY"
