from datetime import datetime

from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelope,
    KnowledgeRecordEnvelopeService,
)
from investment_terminal.knowledge.repository import (
    KnowledgeRecordRepository,
)


class KnowledgeQueryService:
    def __init__(
        self,
        *,
        repository: KnowledgeRecordRepository,
        envelope_service: KnowledgeRecordEnvelopeService | None = None,
    ) -> None:
        if not isinstance(repository, KnowledgeRecordRepository):
            raise TypeError("repository must be a KnowledgeRecordRepository")
        self._repository = repository
        self._envelope_service = (
            envelope_service
            if envelope_service is not None
            else KnowledgeRecordEnvelopeService()
        )

    def get(self, knowledge_id: str, version: int) -> KnowledgeRecordEnvelope | None:
        record = self._repository.get(knowledge_id, version)
        if record is None:
            return None
        return self._envelope_service.build(record)

    def require(self, knowledge_id: str, version: int) -> KnowledgeRecordEnvelope:
        return self._envelope_service.build(
            self._repository.require(knowledge_id, version)
        )

    def list_all(self) -> tuple[KnowledgeRecordEnvelope, ...]:
        return self._envelope_service.build_many(
            self._repository.list_all()
        )

    def find_by_subject(
        self,
        subject_key: str,
    ) -> tuple[KnowledgeRecordEnvelope, ...]:
        return self._envelope_service.build_many(
            self._repository.find_by_subject(subject_key)
        )

    def find_valid_at(
        self,
        subject_key: str,
        *,
        at: datetime,
    ) -> tuple[KnowledgeRecordEnvelope, ...]:
        return self._envelope_service.build_many(
            self._repository.find_valid_at(
                subject_key,
                at=at,
            )
        )

    def latest_for_subject(
        self,
        subject_key: str,
    ) -> KnowledgeRecordEnvelope | None:
        record = self._repository.latest_for_subject(subject_key)
        if record is None:
            return None
        return self._envelope_service.build(record)
