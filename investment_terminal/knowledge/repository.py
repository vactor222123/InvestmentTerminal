"""
Knowledge repository abstraction and deterministic reference implementation.

The Knowledge Domain owns query semantics. Concrete persistence adapters,
including SQLite, must implement this contract without changing ordering or
validity behavior.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from investment_terminal.knowledge.models import KnowledgeRecord
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class KnowledgeRecordRepository(ABC):
    """Persistence-agnostic repository contract for versioned knowledge."""

    @abstractmethod
    def add(
        self,
        record: KnowledgeRecord,
    ) -> KnowledgeRecord:
        """Persist one exact knowledge identity or reject a duplicate."""

    @abstractmethod
    def get(
        self,
        knowledge_id: str,
        version: int,
    ) -> KnowledgeRecord | None:
        """Return one exact knowledge version, or None when absent."""

    def require(
        self,
        knowledge_id: str,
        version: int,
    ) -> KnowledgeRecord:
        record = self.get(
            knowledge_id,
            version,
        )
        if record is None:
            raise KeyError(
                f"No knowledge record found for "
                f"{knowledge_id}@{version}"
            )
        return record

    @abstractmethod
    def list_all(
        self,
    ) -> tuple[KnowledgeRecord, ...]:
        """
        Return all records ordered by:
        generated_at, knowledge_id, version.
        """

    @abstractmethod
    def find_by_subject(
        self,
        subject_key: str,
    ) -> tuple[KnowledgeRecord, ...]:
        """
        Return subject records ordered by:
        valid_from, generated_at, knowledge_id, version.
        """

    @abstractmethod
    def find_valid_at(
        self,
        subject_key: str,
        *,
        at: datetime,
    ) -> tuple[KnowledgeRecord, ...]:
        """
        Return records valid at an exact instant.

        Validity is inclusive:
        valid_from <= at <= valid_to
        or valid_to is None.
        """

    @abstractmethod
    def latest_for_subject(
        self,
        subject_key: str,
    ) -> KnowledgeRecord | None:
        """
        Return the deterministic latest subject record ordered by:
        generated_at, knowledge_id, version.
        """


class InMemoryKnowledgeRecordRepository(
    KnowledgeRecordRepository
):
    """
    Reference implementation for repository semantics.

    This is not canonical persistence. It exists to make the repository
    contract executable before a concrete storage adapter is introduced.
    """

    def __init__(self) -> None:
        self._records: dict[
            tuple[str, int],
            KnowledgeRecord,
        ] = {}

    def add(
        self,
        record: KnowledgeRecord,
    ) -> KnowledgeRecord:
        if not isinstance(
            record,
            KnowledgeRecord,
        ):
            raise TypeError(
                "record must be a KnowledgeRecord"
            )

        key = (
            record.knowledge_id,
            record.version,
        )
        if key in self._records:
            raise ValueError(
                "Knowledge record identity already exists"
            )

        self._records[key] = record
        return record

    def get(
        self,
        knowledge_id: str,
        version: int,
    ) -> KnowledgeRecord | None:
        normalized_id = normalize_required_text(
            knowledge_id,
            field_name="knowledge_id",
        )
        normalized_version = self._normalize_version(
            version
        )

        return self._records.get(
            (
                normalized_id,
                normalized_version,
            )
        )

    def list_all(
        self,
    ) -> tuple[KnowledgeRecord, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda record: (
                    record.generated_at,
                    record.knowledge_id,
                    record.version,
                ),
            )
        )

    def find_by_subject(
        self,
        subject_key: str,
    ) -> tuple[KnowledgeRecord, ...]:
        normalized_subject = normalize_required_text(
            subject_key,
            field_name="subject_key",
        )
        return tuple(
            sorted(
                (
                    record
                    for record in self._records.values()
                    if record.subject_key == normalized_subject
                ),
                key=lambda record: (
                    record.valid_from,
                    record.generated_at,
                    record.knowledge_id,
                    record.version,
                ),
            )
        )

    def find_valid_at(
        self,
        subject_key: str,
        *,
        at: datetime,
    ) -> tuple[KnowledgeRecord, ...]:
        validate_aware_datetime(
            at,
            field_name="at",
        )
        records = self.find_by_subject(
            subject_key
        )

        return tuple(
            record
            for record in records
            if (
                record.valid_from <= at
                and (
                    record.valid_to is None
                    or at <= record.valid_to
                )
            )
        )

    def latest_for_subject(
        self,
        subject_key: str,
    ) -> KnowledgeRecord | None:
        normalized_subject = normalize_required_text(
            subject_key,
            field_name="subject_key",
        )
        records = tuple(
            record
            for record in self._records.values()
            if record.subject_key == normalized_subject
        )
        if not records:
            return None

        return max(
            records,
            key=lambda record: (
                record.generated_at,
                record.knowledge_id,
                record.version,
            ),
        )

    @staticmethod
    def _normalize_version(
        version: int,
    ) -> int:
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version <= 0
        ):
            raise ValueError(
                "version must be a positive integer"
            )
        return version
