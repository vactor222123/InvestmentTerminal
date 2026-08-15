"""
Deterministic ingestion of neutral historical evidence into Knowledge.

This service deliberately knows nothing about the History package. Translation
from verified History models into HistoricalSnapshotKnowledgeSource remains a
composition-boundary responsibility.
"""

from datetime import datetime

from investment_terminal.knowledge.models import KnowledgeRecord
from investment_terminal.knowledge.projection import (
    HistoricalSnapshotKnowledgeProjectionService,
    HistoricalSnapshotKnowledgeSource,
)
from investment_terminal.knowledge.repository import (
    KnowledgeRecordRepository,
)


class HistoricalSnapshotKnowledgeIngestionService:
    """
    Project and persist immutable snapshot-backed Knowledge versions.

    Idempotency is defined only for an exact existing identity whose persisted
    record is byte-for-contract equivalent to the newly projected record.
    Conflicting reuse of the same knowledge_id/version fails closed.
    """

    def __init__(
        self,
        *,
        repository: KnowledgeRecordRepository,
        projection_service: (
            HistoricalSnapshotKnowledgeProjectionService | None
        ) = None,
    ) -> None:
        if not isinstance(repository, KnowledgeRecordRepository):
            raise TypeError(
                "repository must be a KnowledgeRecordRepository"
            )

        self._repository = repository
        self._projection_service = (
            projection_service
            if projection_service is not None
            else HistoricalSnapshotKnowledgeProjectionService()
        )

    def ingest(
        self,
        source: HistoricalSnapshotKnowledgeSource,
        *,
        subject_key: str,
        generated_at: datetime,
        version: int = 1,
    ) -> KnowledgeRecord:
        """
        Project and persist one immutable Knowledge version.

        Repeating the exact same ingestion is idempotent. Reusing the same
        knowledge identity/version for a different record is rejected.
        """
        record = self._projection_service.project(
            source,
            subject_key=subject_key,
            generated_at=generated_at,
            version=version,
        )

        existing = self._repository.get(
            record.knowledge_id,
            record.version,
        )
        if existing is not None:
            if existing == record:
                return existing
            raise ValueError(
                "Knowledge record identity already exists with "
                "different content"
            )

        persisted = self._repository.add(record)

        if persisted != record:
            raise RuntimeError(
                "Knowledge repository must preserve the projected record"
            )

        return persisted
