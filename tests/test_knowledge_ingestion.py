from datetime import datetime, timezone

import pytest

from investment_terminal.knowledge.ingestion import (
    HistoricalSnapshotKnowledgeIngestionService,
)
from investment_terminal.knowledge.models import (
    KnowledgeRecord,
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


def service_and_repository():
    repository = InMemoryKnowledgeRecordRepository()
    service = HistoricalSnapshotKnowledgeIngestionService(
        repository=repository,
    )
    return service, repository


def test_ingest_projects_and_persists_exact_record() -> None:
    service, repository = service_and_repository()

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


def test_exact_reingestion_is_idempotent() -> None:
    service, repository = service_and_repository()

    first = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=2,
    )
    second = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=2,
    )

    assert second == first
    assert repository.list_all() == (first,)


def test_same_identity_with_different_content_fails_closed() -> None:
    service, repository = service_and_repository()

    first = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=2,
    )

    with pytest.raises(
        ValueError,
        match="identity already exists with different content",
    ):
        service.ingest(
            source(),
            subject_key="WORLD",
            generated_at=dt(12),
            version=2,
        )

    assert repository.list_all() == (first,)


def test_explicit_new_version_creates_separate_immutable_record() -> None:
    service, repository = service_and_repository()

    version_one = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=1,
    )
    version_two = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(13),
        version=2,
    )

    assert version_one.knowledge_id == version_two.knowledge_id
    assert version_one.version == 1
    assert version_two.version == 2
    assert repository.require(
        version_one.knowledge_id,
        1,
    ) == version_one
    assert repository.require(
        version_two.knowledge_id,
        2,
    ) == version_two


def test_ingestion_never_auto_increments_version() -> None:
    service, repository = service_and_repository()

    first = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
        version=1,
    )

    with pytest.raises(
        ValueError,
        match="identity already exists with different content",
    ):
        service.ingest(
            source(),
            subject_key="portfolio",
            generated_at=dt(13),
            version=1,
        )

    assert repository.list_all() == (first,)


def test_existing_identity_check_occurs_before_add() -> None:
    class NoDuplicateAddRepository(
        InMemoryKnowledgeRecordRepository
    ):
        def add(
            self,
            record: KnowledgeRecord,
        ) -> KnowledgeRecord:
            if self.get(
                record.knowledge_id,
                record.version,
            ) is not None:
                raise AssertionError(
                    "idempotent reingestion must not call add"
                )
            return super().add(record)

    repository = NoDuplicateAddRepository()
    service = HistoricalSnapshotKnowledgeIngestionService(
        repository=repository,
    )

    first = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
    )
    second = service.ingest(
        source(),
        subject_key="portfolio",
        generated_at=dt(12),
    )

    assert second == first


def test_ingest_leaves_projection_validation_fail_closed() -> None:
    service, repository = service_and_repository()

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
