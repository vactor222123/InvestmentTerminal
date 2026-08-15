from datetime import datetime, timezone

import pytest

from investment_terminal.knowledge.ingestion import (
    HistoricalSnapshotKnowledgeIngestionService,
)
from investment_terminal.knowledge.projection import (
    HistoricalSnapshotKnowledgeSource,
)
from investment_terminal.knowledge.repository import (
    InMemoryKnowledgeRecordRepository,
)


SNAPSHOT_ID = "11111111-1111-4111-8111-111111111111"


def dt(hour: int) -> datetime:
    return datetime(2026, 8, 15, hour, 0, tzinfo=timezone.utc)


def source() -> HistoricalSnapshotKnowledgeSource:
    return HistoricalSnapshotKnowledgeSource(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        generated_at=dt(10),
        archived_at=dt(11),
        checksum_sha256="a" * 64,
    )


def test_ingest_projects_and_persists_exact_record() -> None:
    repository = InMemoryKnowledgeRecordRepository()
    service = HistoricalSnapshotKnowledgeIngestionService(
        repository=repository,
    )

    result = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
    )

    assert result.knowledge_id == (
        f"HISTORICAL_SNAPSHOT_FACT:{SNAPSHOT_ID}"
    )
    assert result.version == 1
    assert result.subject_key == "portfolio"
    assert repository.require(
        result.knowledge_id,
        result.version,
    ) == result


def test_ingest_is_deterministic_for_same_explicit_inputs() -> None:
    first_repository = InMemoryKnowledgeRecordRepository()
    second_repository = InMemoryKnowledgeRecordRepository()

    first = HistoricalSnapshotKnowledgeIngestionService(
        repository=first_repository,
    ).ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=3,
    )
    second = HistoricalSnapshotKnowledgeIngestionService(
        repository=second_repository,
    ).ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=3,
    )

    assert first == second


def test_ingest_preserves_explicit_version() -> None:
    repository = InMemoryKnowledgeRecordRepository()

    result = HistoricalSnapshotKnowledgeIngestionService(
        repository=repository,
    ).ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=4,
    )

    assert result.version == 4
    assert repository.require(
        result.knowledge_id,
        4,
    ) == result


def test_ingest_does_not_hide_duplicate_identity() -> None:
    repository = InMemoryKnowledgeRecordRepository()
    service = HistoricalSnapshotKnowledgeIngestionService(
        repository=repository,
    )

    service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
    )

    with pytest.raises(
        ValueError,
        match="identity already exists",
    ):
        service.ingest(
            source(),
            subject_key="portfolio",
            generated_at=dt(12),
        )


def test_ingest_leaves_projection_validation_fail_closed() -> None:
    repository = InMemoryKnowledgeRecordRepository()
    service = HistoricalSnapshotKnowledgeIngestionService(
        repository=repository,
    )

    with pytest.raises(
        ValueError,
        match="generated_at must not be earlier",
    ):
        service.ingest(
            source(),
            subject_key="portfolio",
            generated_at=dt(9),
        )

    assert repository.list_all() == ()
