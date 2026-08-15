"""Repository contract for durable admissible grounded generations."""

from abc import ABC, abstractmethod
from datetime import datetime

from investment_terminal.ai.generation_persistence_models import PersistedGroundedGeneration
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


def _validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    return limit


def _validate_window(started_at: datetime, ended_at: datetime) -> tuple[datetime, datetime]:
    start = validate_aware_datetime(started_at, field_name="started_at")
    end = validate_aware_datetime(ended_at, field_name="ended_at")
    if end <= start:
        raise ValueError("ended_at must be later than started_at")
    return start, end


class GroundedGenerationRepository(ABC):
    @abstractmethod
    def add(self, record: PersistedGroundedGeneration) -> PersistedGroundedGeneration:
        ...

    @abstractmethod
    def get(self, request_id: str) -> PersistedGroundedGeneration | None:
        ...

    def require(self, request_id: str) -> PersistedGroundedGeneration:
        record = self.get(request_id)
        if record is None:
            raise KeyError(f"No persisted grounded generation found for {request_id}")
        return record

    @abstractmethod
    def list_all(self) -> tuple[PersistedGroundedGeneration, ...]:
        ...

    @abstractmethod
    def list_recent(self, limit: int) -> tuple[PersistedGroundedGeneration, ...]:
        ...

    @abstractmethod
    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[PersistedGroundedGeneration, ...]:
        ...


class InMemoryGroundedGenerationRepository(GroundedGenerationRepository):
    def __init__(self) -> None:
        self._records: dict[str, PersistedGroundedGeneration] = {}

    def add(self, record: PersistedGroundedGeneration) -> PersistedGroundedGeneration:
        if not isinstance(record, PersistedGroundedGeneration):
            raise TypeError("record must be a PersistedGroundedGeneration")
        if record.request_id in self._records:
            raise ValueError("Grounded generation request identity already exists")
        self._records[record.request_id] = record
        return record

    def get(self, request_id: str) -> PersistedGroundedGeneration | None:
        return self._records.get(
            normalize_required_text(request_id, field_name="request_id")
        )

    def list_all(self) -> tuple[PersistedGroundedGeneration, ...]:
        return tuple(sorted(
            self._records.values(),
            key=lambda record: (record.generated_at, record.request_id),
        ))

    def list_recent(self, limit: int) -> tuple[PersistedGroundedGeneration, ...]:
        validated_limit = _validate_limit(limit)
        return tuple(sorted(
            self._records.values(),
            key=lambda record: (record.generated_at, record.request_id),
            reverse=True,
        )[:validated_limit])

    def list_between(
        self,
        started_at: datetime,
        ended_at: datetime,
    ) -> tuple[PersistedGroundedGeneration, ...]:
        start, end = _validate_window(started_at, ended_at)
        return tuple(
            record for record in self.list_all()
            if start <= record.generated_at < end
        )
