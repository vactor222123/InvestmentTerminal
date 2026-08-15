"""Repository contract for durable admissible grounded generations."""

from abc import ABC, abstractmethod

from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.utils.validation import normalize_required_text


class GroundedGenerationRepository(ABC):
    """
    Persistence boundary for generated evidence.

    Records are immutable by request identity and remain downstream of
    Knowledge; this repository grants no History or Knowledge authority.
    """

    @abstractmethod
    def add(
        self,
        record: PersistedGroundedGeneration,
    ) -> PersistedGroundedGeneration:
        """Persist one exact request identity or reject a duplicate."""

    @abstractmethod
    def get(
        self,
        request_id: str,
    ) -> PersistedGroundedGeneration | None:
        """Return one exact persisted generation, or None."""

    def require(
        self,
        request_id: str,
    ) -> PersistedGroundedGeneration:
        record = self.get(request_id)
        if record is None:
            raise KeyError(
                f"No persisted grounded generation found for {request_id}"
            )
        return record

    @abstractmethod
    def list_all(
        self,
    ) -> tuple[PersistedGroundedGeneration, ...]:
        """Return records ordered by generated_at then request_id."""


class InMemoryGroundedGenerationRepository(
    GroundedGenerationRepository
):
    """Executable reference adapter for immutable repository semantics."""

    def __init__(self) -> None:
        self._records: dict[
            str,
            PersistedGroundedGeneration,
        ] = {}

    def add(
        self,
        record: PersistedGroundedGeneration,
    ) -> PersistedGroundedGeneration:
        if not isinstance(
            record,
            PersistedGroundedGeneration,
        ):
            raise TypeError(
                "record must be a PersistedGroundedGeneration"
            )
        if record.request_id in self._records:
            raise ValueError(
                "Grounded generation request identity already exists"
            )
        self._records[record.request_id] = record
        return record

    def get(
        self,
        request_id: str,
    ) -> PersistedGroundedGeneration | None:
        normalized = normalize_required_text(
            request_id,
            field_name="request_id",
        )
        return self._records.get(normalized)

    def list_all(
        self,
    ) -> tuple[PersistedGroundedGeneration, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda record: (
                    record.generated_at,
                    record.request_id,
                ),
            )
        )
