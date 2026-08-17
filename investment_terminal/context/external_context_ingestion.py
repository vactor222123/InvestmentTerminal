"""Provider-neutral external-context ingestion boundary."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Integral
from typing import Any, Protocol

from investment_terminal.context.external_context_models import (
    EXTERNAL_CONTEXT_TYPES,
    ExternalContextEvidence,
    ExternalContextProvenance,
    ExternalContextQualityService,
    ExternalContextRecord,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class ExternalContextQuery:
    """Provider-independent request for a bounded context window."""

    context_types: tuple[str, ...]
    subjects: tuple[str, ...]
    published_from: datetime
    published_until: datetime
    maximum_age_hours: float
    limit: int

    def __post_init__(self) -> None:
        context_types = _normalize_unique_text_tuple(
            self.context_types,
            field_name="context_types",
            uppercase=True,
            allow_empty=False,
        )
        unsupported = tuple(
            value
            for value in context_types
            if value not in EXTERNAL_CONTEXT_TYPES
        )
        if unsupported:
            raise ValueError(
                "context_types contains unsupported values: "
                + ", ".join(unsupported)
            )
        subjects = _normalize_unique_text_tuple(
            self.subjects,
            field_name="subjects",
            uppercase=True,
            allow_empty=True,
        )
        validate_aware_datetime(
            self.published_from,
            field_name="published_from",
        )
        validate_aware_datetime(
            self.published_until,
            field_name="published_until",
        )
        if self.published_until <= self.published_from:
            raise ValueError(
                "published_until must be later than published_from"
            )
        maximum_age = _validate_positive_number(
            self.maximum_age_hours,
            field_name="maximum_age_hours",
        )
        if (
            isinstance(self.limit, bool)
            or not isinstance(self.limit, Integral)
            or self.limit <= 0
        ):
            raise ValueError("limit must be a positive integer")

        object.__setattr__(self, "context_types", context_types)
        object.__setattr__(self, "subjects", subjects)
        object.__setattr__(self, "maximum_age_hours", maximum_age)
        object.__setattr__(self, "limit", int(self.limit))

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_types": list(self.context_types),
            "subjects": list(self.subjects),
            "published_from": self.published_from.isoformat(),
            "published_until": self.published_until.isoformat(),
            "maximum_age_hours": self.maximum_age_hours,
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ExternalContextSourceItem:
    """Normalized provider output before deterministic quality assessment."""

    record: ExternalContextRecord
    provenance: ExternalContextProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.record, ExternalContextRecord):
            raise TypeError("record must be an ExternalContextRecord")
        if not isinstance(self.provenance, ExternalContextProvenance):
            raise TypeError("provenance must be ExternalContextProvenance")


class ExternalContextProvider(Protocol):
    """Contract implemented by external-context provider adapters."""

    def fetch(
        self,
        query: ExternalContextQuery,
    ) -> tuple[ExternalContextSourceItem, ...]:
        """Return normalized source items for one bounded query."""
        ...


@dataclass(frozen=True, slots=True)
class ExternalContextIngestionResult:
    """Deterministic evidence returned by one provider ingestion call."""

    query: ExternalContextQuery
    checked_at: datetime
    evidence: tuple[ExternalContextEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.query, ExternalContextQuery):
            raise TypeError("query must be an ExternalContextQuery")
        validate_aware_datetime(self.checked_at, field_name="checked_at")
        _validate_tuple_members(
            self.evidence,
            field_name="evidence",
            expected_type=ExternalContextEvidence,
        )
        if any(
            item.quality.checked_at != self.checked_at
            for item in self.evidence
        ):
            raise ValueError(
                "evidence quality timestamps must match checked_at"
            )

    @property
    def status_counts(self) -> dict[str, int]:
        counts = Counter(item.quality.status for item in self.evidence)
        return {
            status: counts[status]
            for status in ("READY", "PARTIAL", "STALE")
        }

    @property
    def all_ready(self) -> bool:
        return bool(self.evidence) and all(
            item.quality.is_ready for item in self.evidence
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "checked_at": self.checked_at.isoformat(),
            "evidence_count": len(self.evidence),
            "status_counts": self.status_counts,
            "all_ready": self.all_ready,
            "evidence": [item.to_dict() for item in self.evidence],
        }


class ExternalContextIngestionService:
    """Acquire normalized context and enforce the requested evidence scope."""

    def __init__(
        self,
        provider: ExternalContextProvider,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if provider is None or not callable(getattr(provider, "fetch", None)):
            raise TypeError("provider must implement fetch(query)")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self._provider = provider
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def ingest(
        self,
        query: ExternalContextQuery,
    ) -> ExternalContextIngestionResult:
        if not isinstance(query, ExternalContextQuery):
            raise TypeError("query must be an ExternalContextQuery")
        checked_at = self._clock()
        validate_aware_datetime(checked_at, field_name="clock result")

        source_items = self._provider.fetch(query)
        _validate_tuple_members(
            source_items,
            field_name="provider result",
            expected_type=ExternalContextSourceItem,
        )
        if len(source_items) > query.limit:
            raise ValueError("provider result exceeds query limit")

        seen_context_ids: set[str] = set()
        seen_source_ids: set[tuple[str, str]] = set()
        evidence: list[ExternalContextEvidence] = []

        for item in source_items:
            self._validate_scope(item, query, checked_at=checked_at)
            context_id = item.record.context_id
            source_id = (
                item.provenance.source,
                item.provenance.source_record_id,
            )
            if context_id in seen_context_ids:
                raise ValueError(
                    "provider result contains duplicate context_id"
                )
            if source_id in seen_source_ids:
                raise ValueError(
                    "provider result contains duplicate source identity"
                )
            seen_context_ids.add(context_id)
            seen_source_ids.add(source_id)

            quality = ExternalContextQualityService.assess(
                item.provenance,
                checked_at=checked_at,
                maximum_age_hours=query.maximum_age_hours,
            )
            evidence.append(ExternalContextEvidence(
                record=item.record,
                provenance=item.provenance,
                quality=quality,
            ))

        evidence.sort(key=lambda item: (
            item.provenance.published_at,
            item.provenance.source,
            item.provenance.source_record_id,
            item.record.context_id,
        ))
        return ExternalContextIngestionResult(
            query=query,
            checked_at=checked_at,
            evidence=tuple(evidence),
        )

    @staticmethod
    def _validate_scope(
        item: ExternalContextSourceItem,
        query: ExternalContextQuery,
        *,
        checked_at: datetime,
    ) -> None:
        if item.record.context_type not in query.context_types:
            raise ValueError("provider returned context_type outside query")
        if not (
            query.published_from
            <= item.provenance.published_at
            < query.published_until
        ):
            raise ValueError("provider returned publication outside query window")
        if item.provenance.published_at > checked_at:
            raise ValueError("provider returned future publication")
        requested_subjects = {
            value.casefold() for value in query.subjects
        }
        item_subjects = {
            value.casefold() for value in item.record.subjects
        }
        if requested_subjects and not item_subjects.intersection(
            requested_subjects
        ):
            raise ValueError("provider returned subjects outside query")


def _normalize_unique_text_tuple(
    value: object,
    *,
    field_name: str,
    uppercase: bool,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if not value and not allow_empty:
        raise ValueError(f"{field_name} must not be empty")
    normalized = tuple(
        normalize_required_text(
            item,
            field_name=f"{field_name} item",
            uppercase=uppercase,
        )
        for item in value
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def _validate_tuple_members(
    value: object,
    *,
    field_name: str,
    expected_type: type,
) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if any(not isinstance(item, expected_type) for item in value):
        raise TypeError(
            f"{field_name} must contain only {expected_type.__name__} objects"
        )


def _validate_positive_number(value: object, *, field_name: str) -> float:
    normalized = validate_finite_number(value, field_name=field_name)
    if normalized <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return normalized
