"""Append-only repository boundary for external-context evidence."""

from abc import ABC, abstractmethod
from datetime import datetime

from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class ExternalContextRepository(ABC):
    """Persistence-agnostic append-only external-context repository."""

    @abstractmethod
    def add(self, evidence: ExternalContextEvidence) -> ExternalContextEvidence:
        """Append evidence or reject its immutable identities."""

    @abstractmethod
    def get(self, context_id: str) -> ExternalContextEvidence | None:
        """Return evidence by canonical context identity."""

    def require(self, context_id: str) -> ExternalContextEvidence:
        evidence = self.get(context_id)
        if evidence is None:
            raise KeyError(f"No external context found for {context_id}")
        return evidence

    @abstractmethod
    def list_all(self) -> tuple[ExternalContextEvidence, ...]:
        """Return evidence ordered by publication and identity."""

    @abstractmethod
    def list_between(
        self,
        published_from: datetime,
        published_until: datetime,
    ) -> tuple[ExternalContextEvidence, ...]:
        """Return evidence in the half-open publication interval."""

    @abstractmethod
    def list_by_subject(self, subject: str) -> tuple[ExternalContextEvidence, ...]:
        """Return evidence whose normalized subjects contain subject."""


class InMemoryExternalContextRepository(ExternalContextRepository):
    """Reference implementation of immutable context append semantics."""

    def __init__(self) -> None:
        self._evidence: dict[str, ExternalContextEvidence] = {}
        self._source_identities: set[tuple[str, str]] = set()

    def add(self, evidence: ExternalContextEvidence) -> ExternalContextEvidence:
        if not isinstance(evidence, ExternalContextEvidence):
            raise TypeError("evidence must be ExternalContextEvidence")
        context_id = evidence.record.context_id
        source_identity = (
            evidence.provenance.source,
            evidence.provenance.source_record_id,
        )
        if context_id in self._evidence:
            raise ValueError("External context identity already exists")
        if source_identity in self._source_identities:
            raise ValueError("External context source identity already exists")
        self._evidence[context_id] = evidence
        self._source_identities.add(source_identity)
        return evidence

    def get(self, context_id: str) -> ExternalContextEvidence | None:
        normalized = normalize_required_text(context_id, field_name="context_id")
        return self._evidence.get(normalized)

    def list_all(self) -> tuple[ExternalContextEvidence, ...]:
        return tuple(sorted(self._evidence.values(), key=_ordering_key))

    def list_between(
        self,
        published_from: datetime,
        published_until: datetime,
    ) -> tuple[ExternalContextEvidence, ...]:
        start = validate_aware_datetime(
            published_from, field_name="published_from",
        )
        end = validate_aware_datetime(
            published_until, field_name="published_until",
        )
        if end <= start:
            raise ValueError("published_until must be later than published_from")
        return tuple(
            item for item in self.list_all()
            if start <= item.provenance.published_at < end
        )

    def list_by_subject(self, subject: str) -> tuple[ExternalContextEvidence, ...]:
        normalized = normalize_required_text(subject, field_name="subject").casefold()
        return tuple(
            item for item in self.list_all()
            if normalized in {
                value.casefold() for value in item.record.subjects
            }
        )


def _ordering_key(evidence: ExternalContextEvidence) -> tuple[object, ...]:
    return (
        evidence.provenance.published_at,
        evidence.provenance.source,
        evidence.provenance.source_record_id,
        evidence.record.context_id,
    )
