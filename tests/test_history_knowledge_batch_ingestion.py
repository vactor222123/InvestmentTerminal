from datetime import datetime, timezone

import pytest

from investment_terminal.cli.history_knowledge import (
    HistoricalSnapshotKnowledgeBatchIngestionService,
    HistoricalSnapshotKnowledgeBatchItem,
)
from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.knowledge.ingestion import (
    HistoricalSnapshotKnowledgeIngestionService,
)
from investment_terminal.knowledge.repository import (
    InMemoryKnowledgeRecordRepository,
)


SNAPSHOT_A = "11111111-1111-4111-8111-111111111111"
SNAPSHOT_B = "22222222-2222-4222-8222-222222222222"
SNAPSHOT_C = "33333333-3333-4333-8333-333333333333"


def dt(day: int, hour: int = 0) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        0,
        tzinfo=timezone.utc,
    )


def snapshot(
    snapshot_id: str,
    *,
    generated_at: datetime,
    archived_at: datetime,
) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        snapshot_id=snapshot_id,
        package_id=f"pkg-{snapshot_id[:4]}",
        package_schema_version="1",
        product_version="27.0",
        generated_at=generated_at,
        archived_at=archived_at,
        relative_path=f"{snapshot_id}.json",
        checksum_sha256=snapshot_id[0] * 64,
    )


def state(
    snapshot_id: str,
    status: str,
    *,
    at: datetime,
) -> HistoricalImportState:
    verified_at = (
        at
        if status in ("VERIFIED", "IMPORTING", "IMPORTED")
        else None
    )
    imported_at = at if status == "IMPORTED" else None

    return HistoricalImportState(
        snapshot_id=snapshot_id,
        status=status,
        metadata_synchronized_at=dt(1),
        package_verified_at=verified_at,
        details_imported_at=imported_at,
        timeline_built_at=imported_at,
        importer_version=(
            "27.0"
            if status in ("IMPORTING", "IMPORTED")
            else None
        ),
        failure_reason=(
            "verification failed"
            if status == "FAILED"
            else None
        ),
        updated_at=at,
    )


def item(
    snapshot_id: str,
    *,
    generated_at: datetime,
    archived_at: datetime,
    status: str = "VERIFIED",
) -> HistoricalSnapshotKnowledgeBatchItem:
    return HistoricalSnapshotKnowledgeBatchItem(
        snapshot=snapshot(
            snapshot_id,
            generated_at=generated_at,
            archived_at=archived_at,
        ),
        import_state=state(
            snapshot_id,
            status,
            at=max(archived_at, dt(10)),
        ),
    )


def service():
    repository = InMemoryKnowledgeRecordRepository()
    ingestion = HistoricalSnapshotKnowledgeIngestionService(
        repository=repository,
    )
    batch = HistoricalSnapshotKnowledgeBatchIngestionService(
        ingestion_service=ingestion,
    )
    return batch, repository


def test_batch_ingests_verified_items_in_canonical_snapshot_order() -> None:
    batch, repository = service()

    results = batch.ingest(
        (
            item(
                SNAPSHOT_C,
                generated_at=dt(3),
                archived_at=dt(4),
            ),
            item(
                SNAPSHOT_A,
                generated_at=dt(1),
                archived_at=dt(2),
            ),
            item(
                SNAPSHOT_B,
                generated_at=dt(2),
                archived_at=dt(3),
            ),
        ),
        subject_key="portfolio",
        generated_at=dt(20),
    )

    assert tuple(
        record.evidence[0].evidence_id
        for record in results
    ) == (
        SNAPSHOT_A,
        SNAPSHOT_B,
        SNAPSHOT_C,
    )
    assert repository.list_all() == results


def test_batch_skips_non_verified_lifecycle_states() -> None:
    batch, repository = service()

    results = batch.ingest(
        (
            item(
                SNAPSHOT_A,
                generated_at=dt(1),
                archived_at=dt(2),
                status="METADATA_ONLY",
            ),
            item(
                SNAPSHOT_B,
                generated_at=dt(2),
                archived_at=dt(3),
                status="VERIFIED",
            ),
            item(
                SNAPSHOT_C,
                generated_at=dt(3),
                archived_at=dt(4),
                status="FAILED",
            ),
        ),
        subject_key="portfolio",
        generated_at=dt(20),
    )

    assert len(results) == 1
    assert results[0].evidence[0].evidence_id == SNAPSHOT_B
    assert repository.list_all() == results


def test_batch_accepts_importing_and_imported_verified_evidence() -> None:
    batch, _ = service()

    results = batch.ingest(
        (
            item(
                SNAPSHOT_A,
                generated_at=dt(1),
                archived_at=dt(2),
                status="IMPORTING",
            ),
            item(
                SNAPSHOT_B,
                generated_at=dt(2),
                archived_at=dt(3),
                status="IMPORTED",
            ),
        ),
        subject_key="portfolio",
        generated_at=dt(20),
    )

    assert tuple(
        record.evidence[0].evidence_id
        for record in results
    ) == (
        SNAPSHOT_A,
        SNAPSHOT_B,
    )


def test_batch_reingestion_is_idempotent() -> None:
    batch, repository = service()
    items = (
        item(
            SNAPSHOT_A,
            generated_at=dt(1),
            archived_at=dt(2),
        ),
        item(
            SNAPSHOT_B,
            generated_at=dt(2),
            archived_at=dt(3),
        ),
    )

    first = batch.ingest(
        items,
        subject_key="portfolio",
        generated_at=dt(20),
        version=2,
    )
    second = batch.ingest(
        tuple(reversed(items)),
        subject_key="portfolio",
        generated_at=dt(20),
        version=2,
    )

    assert second == first
    assert repository.list_all() == first


def test_batch_preserves_explicit_version_for_every_record() -> None:
    batch, _ = service()

    results = batch.ingest(
        (
            item(
                SNAPSHOT_A,
                generated_at=dt(1),
                archived_at=dt(2),
            ),
            item(
                SNAPSHOT_B,
                generated_at=dt(2),
                archived_at=dt(3),
            ),
        ),
        subject_key="portfolio",
        generated_at=dt(20),
        version=4,
    )

    assert tuple(record.version for record in results) == (4, 4)


def test_batch_empty_input_is_empty() -> None:
    batch, repository = service()

    assert batch.ingest(
        (),
        subject_key="portfolio",
        generated_at=dt(20),
    ) == ()
    assert repository.list_all() == ()


def test_batch_item_rejects_mismatched_identity() -> None:
    with pytest.raises(
        ValueError,
        match="snapshot_id must match",
    ):
        HistoricalSnapshotKnowledgeBatchItem(
            snapshot=snapshot(
                SNAPSHOT_A,
                generated_at=dt(1),
                archived_at=dt(2),
            ),
            import_state=state(
                SNAPSHOT_B,
                "VERIFIED",
                at=dt(10),
            ),
        )


def test_batch_rejects_non_batch_items() -> None:
    batch, _ = service()

    with pytest.raises(
        TypeError,
        match="items must contain only",
    ):
        batch.ingest(
            (object(),),  # type: ignore[arg-type]
            subject_key="portfolio",
            generated_at=dt(20),
        )
