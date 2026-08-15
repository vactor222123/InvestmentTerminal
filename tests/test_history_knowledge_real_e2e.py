"""
Real end-to-end History → Knowledge ingestion fixture.

The flow crosses only public/canonical boundaries:

Review Package
→ immutable archive
→ manifest
→ History SQLite synchronization
→ verified historical package import
→ History import state
→ History → Knowledge CLI composition
→ Knowledge SQLite persistence
→ exact evidence identity/checksum preservation
→ idempotent reingestion
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from investment_terminal.cli.ingest_history_knowledge import (
    main as ingest_history_knowledge,
)
from investment_terminal.history.historical_import_pipeline import (
    HistoricalImportPipeline,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_manifest_import_service import (
    HistoricalManifestImportService,
)
from investment_terminal.history.historical_review_package_loader import (
    HistoricalReviewPackageLoader,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_archive import (
    HistoricalSnapshotArchive,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "history"
)

FIRST_ID = "11111111-1111-4111-8111-111111111111"
SECOND_ID = "22222222-2222-4222-8222-222222222222"

FIRST_ARCHIVED_AT = datetime(
    2026,
    8,
    1,
    8,
    0,
    tzinfo=timezone.utc,
)
SECOND_ARCHIVED_AT = datetime(
    2026,
    9,
    1,
    8,
    0,
    tzinfo=timezone.utc,
)
SYNC_AT = datetime(
    2026,
    9,
    1,
    9,
    0,
    tzinfo=timezone.utc,
)
KNOWLEDGE_GENERATED_AT = datetime(
    2026,
    9,
    1,
    10,
    0,
    tzinfo=timezone.utc,
)


def _copy_fixture(
    tmp_path: Path,
    name: str,
) -> Path:
    source = FIXTURE_ROOT / name
    destination = tmp_path / "source" / name
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    destination.write_bytes(
        source.read_bytes()
    )
    return destination


def _archive(
    *,
    history_root: Path,
    source: Path,
    snapshot_id: str,
    archived_at: datetime,
    supersedes: str | None = None,
):
    archive = HistoricalSnapshotArchive(
        history_root,
        clock=lambda: archived_at,
        uuid_factory=lambda: UUID(
            snapshot_id
        ),
    )
    return archive.archive(
        source,
        product_version="0.27.0",
        supersedes=supersedes,
    )


def _build_real_imported_history(
    tmp_path: Path,
):
    history_root = tmp_path / "history"

    first_source = _copy_fixture(
        tmp_path,
        "review_package_2026_07.json",
    )
    second_source = _copy_fixture(
        tmp_path,
        "review_package_2026_08.json",
    )

    first = _archive(
        history_root=history_root,
        source=first_source,
        snapshot_id=FIRST_ID,
        archived_at=FIRST_ARCHIVED_AT,
    )
    second = _archive(
        history_root=history_root,
        source=second_source,
        snapshot_id=SECOND_ID,
        archived_at=SECOND_ARCHIVED_AT,
        supersedes=FIRST_ID,
    )

    manifest = HistoricalSnapshotManifest(
        history_root / "manifest.jsonl"
    )
    manifest.append(first)
    manifest.append(second)

    history_database = history_root / "history.db"
    store = HistoricalSQLiteStore(
        history_database
    )
    store.initialize()
    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    snapshots = HistoricalSnapshotRepository(
        store
    )
    states = HistoricalImportStateRepository(
        store
    )

    HistoricalManifestImportService(
        manifest=manifest,
        repository=snapshots,
        state_repository=states,
        clock=lambda: SYNC_AT,
    ).synchronize()

    import_times = iter(
        (
            datetime(2026, 9, 1, 9, 1, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 2, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 3, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 4, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 5, tzinfo=timezone.utc),
            datetime(2026, 9, 1, 9, 6, tzinfo=timezone.utc),
        )
    )
    pipeline = HistoricalImportPipeline(
        store=store,
        loader=HistoricalReviewPackageLoader(
            history_root
        ),
        state_repository=states,
        clock=lambda: next(
            import_times
        ),
    )

    pipeline.import_snapshot(first)
    pipeline.import_snapshot(second)

    return (
        history_database,
        first,
        second,
        states,
    )


def test_real_history_to_knowledge_flow_end_to_end(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (
        history_database,
        first,
        second,
        states,
    ) = _build_real_imported_history(
        tmp_path
    )

    assert states.require(
        FIRST_ID
    ).status == "IMPORTED"
    assert states.require(
        SECOND_ID
    ).status == "IMPORTED"

    knowledge_database = (
        tmp_path
        / "knowledge"
        / "knowledge.db"
    )

    argv = [
        "--history-database",
        str(history_database),
        "--knowledge-database",
        str(knowledge_database),
        "--all",
        "--subject",
        "portfolio",
        "--generated-at",
        KNOWLEDGE_GENERATED_AT.isoformat(),
        "--version",
        "1",
        "--json",
    ]

    ingest_history_knowledge(
        argv
    )
    first_report = json.loads(
        capsys.readouterr().out
    )

    assert first_report[
        "history_snapshots"
    ] == 2
    assert first_report[
        "knowledge_records"
    ] == 2

    repository = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            knowledge_database
        )
    )
    records = repository.list_all()

    assert len(records) == 2

    by_evidence_id = {
        record.evidence[0].evidence_id: record
        for record in records
    }

    assert set(
        by_evidence_id
    ) == {
        FIRST_ID,
        SECOND_ID,
    }

    first_record = by_evidence_id[
        FIRST_ID
    ]
    second_record = by_evidence_id[
        SECOND_ID
    ]

    assert first_record.knowledge_id == (
        f"HISTORICAL_SNAPSHOT_FACT:{FIRST_ID}"
    )
    assert second_record.knowledge_id == (
        f"HISTORICAL_SNAPSHOT_FACT:{SECOND_ID}"
    )

    assert first_record.version == 1
    assert second_record.version == 1
    assert first_record.subject_key == "portfolio"
    assert second_record.subject_key == "portfolio"

    assert first_record.evidence[0].evidence_type == (
        "HISTORICAL_SNAPSHOT"
    )
    assert second_record.evidence[0].evidence_type == (
        "HISTORICAL_SNAPSHOT"
    )

    assert first_record.evidence[0].checksum_sha256 == (
        first.checksum_sha256
    )
    assert second_record.evidence[0].checksum_sha256 == (
        second.checksum_sha256
    )

    assert first_record.evidence[0].observed_at == (
        first.generated_at
    )
    assert second_record.evidence[0].observed_at == (
        second.generated_at
    )

    assert first_record.generated_at == (
        KNOWLEDGE_GENERATED_AT
    )
    assert second_record.generated_at == (
        KNOWLEDGE_GENERATED_AT
    )

    ingest_history_knowledge(
        argv
    )
    second_report = json.loads(
        capsys.readouterr().out
    )

    assert second_report == first_report
    assert repository.list_all() == records


def test_real_history_to_knowledge_preserves_archive_checksum_identity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (
        history_database,
        first,
        second,
        _,
    ) = _build_real_imported_history(
        tmp_path
    )

    knowledge_database = (
        tmp_path
        / "knowledge.db"
    )

    ingest_history_knowledge(
        [
            "--history-database",
            str(history_database),
            "--knowledge-database",
            str(knowledge_database),
            "--all",
            "--subject",
            "portfolio",
            "--generated-at",
            KNOWLEDGE_GENERATED_AT.isoformat(),
            "--json",
        ]
    )
    capsys.readouterr()

    records = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            knowledge_database
        )
    ).list_all()

    evidence = {
        record.evidence[0].evidence_id:
        record.evidence[0].checksum_sha256
        for record in records
    }

    assert evidence == {
        FIRST_ID: first.checksum_sha256,
        SECOND_ID: second.checksum_sha256,
    }
