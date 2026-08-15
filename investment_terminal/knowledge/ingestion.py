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
    """Project one neutral historical source and persist the exact result."""

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
        """Project and persist one snapshot-backed Knowledge record."""
        record = self._projection_service.project(
            source,
            subject_key=subject_key,
            generated_at=generated_at,
            version=version,
        )
        persisted = self._repository.add(record)

        if persisted != record:
            raise RuntimeError(
                "Knowledge repository must preserve the projected record"
            )

        return persisted
