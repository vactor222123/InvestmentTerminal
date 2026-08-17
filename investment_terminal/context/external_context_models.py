"""Provider-independent external-context evidence contracts."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


EXTERNAL_CONTEXT_TYPES = (
    "NEWS",
    "MACROECONOMIC",
    "GEOPOLITICAL",
    "EVENT",
)
EXTERNAL_CONTEXT_UNCERTAINTY_LEVELS = (
    "NONE",
    "LOW",
    "MEDIUM",
    "HIGH",
    "UNKNOWN",
)
EXTERNAL_CONTEXT_QUALITY_STATUSES = (
    "READY",
    "PARTIAL",
    "STALE",
)


@dataclass(frozen=True, slots=True)
class ExternalContextProvenance:
    """Traceable lineage for one externally acquired context record."""

    source: str
    source_record_id: str
    published_at: datetime
    fetched_at: datetime
    source_url: str | None = None
    checksum_sha256: str | None = None

    def __post_init__(self) -> None:
        validate_aware_datetime(self.published_at, field_name="published_at")
        validate_aware_datetime(self.fetched_at, field_name="fetched_at")
        if self.fetched_at < self.published_at:
            raise ValueError(
                "fetched_at must not be earlier than published_at"
            )

        checksum = normalize_optional_text(
            self.checksum_sha256,
            field_name="checksum_sha256",
            uppercase=False,
        )
        if checksum is not None:
            checksum = checksum.lower()
            if len(checksum) != 64 or any(
                character not in "0123456789abcdef" for character in checksum
            ):
                raise ValueError(
                    "checksum_sha256 must contain 64 hexadecimal characters"
                )

        object.__setattr__(self, "source", normalize_required_text(
            self.source, field_name="source", uppercase=True,
        ))
        object.__setattr__(self, "source_record_id", normalize_required_text(
            self.source_record_id, field_name="source_record_id",
        ))
        object.__setattr__(self, "source_url", normalize_optional_text(
            self.source_url, field_name="source_url",
        ))
        object.__setattr__(self, "checksum_sha256", checksum)

    @property
    def is_fully_traceable(self) -> bool:
        return self.source_url is not None and self.checksum_sha256 is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_record_id": self.source_record_id,
            "published_at": self.published_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "source_url": self.source_url,
            "checksum_sha256": self.checksum_sha256,
            "is_fully_traceable": self.is_fully_traceable,
        }


@dataclass(frozen=True, slots=True)
class ExternalContextRecord:
    """Normalized external fact or report with explicit uncertainty."""

    context_id: str
    context_type: str
    title: str
    summary: str
    subjects: tuple[str, ...]
    uncertainty_level: str
    uncertainty_reasons: tuple[str, ...] = ()
    event_at: datetime | None = None

    def __post_init__(self) -> None:
        context_type = normalize_required_text(
            self.context_type, field_name="context_type", uppercase=True,
        )
        if context_type not in EXTERNAL_CONTEXT_TYPES:
            raise ValueError(
                "context_type must be one of: "
                + ", ".join(EXTERNAL_CONTEXT_TYPES)
            )
        uncertainty_level = normalize_required_text(
            self.uncertainty_level,
            field_name="uncertainty_level",
            uppercase=True,
        )
        if uncertainty_level not in EXTERNAL_CONTEXT_UNCERTAINTY_LEVELS:
            raise ValueError(
                "uncertainty_level must be one of: "
                + ", ".join(EXTERNAL_CONTEXT_UNCERTAINTY_LEVELS)
            )
        _validate_text_tuple(self.subjects, field_name="subjects")
        _validate_text_tuple(
            self.uncertainty_reasons, field_name="uncertainty_reasons",
        )
        if uncertainty_level != "NONE" and not self.uncertainty_reasons:
            raise ValueError(
                "uncertainty_reasons must explain non-NONE uncertainty"
            )
        if self.event_at is not None:
            validate_aware_datetime(self.event_at, field_name="event_at")

        object.__setattr__(self, "context_id", normalize_required_text(
            self.context_id, field_name="context_id",
        ))
        object.__setattr__(self, "context_type", context_type)
        object.__setattr__(self, "title", normalize_required_text(
            self.title, field_name="title",
        ))
        object.__setattr__(self, "summary", normalize_required_text(
            self.summary, field_name="summary",
        ))
        object.__setattr__(self, "subjects", tuple(
            subject.strip() for subject in self.subjects
        ))
        object.__setattr__(self, "uncertainty_level", uncertainty_level)
        object.__setattr__(self, "uncertainty_reasons", tuple(
            reason.strip() for reason in self.uncertainty_reasons
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "context_type": self.context_type,
            "title": self.title,
            "summary": self.summary,
            "subjects": list(self.subjects),
            "uncertainty_level": self.uncertainty_level,
            "uncertainty_reasons": list(self.uncertainty_reasons),
            "event_at": (
                self.event_at.isoformat() if self.event_at is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ExternalContextQualityAssessment:
    """Explicit freshness and lineage quality for external context."""

    status: str
    checked_at: datetime
    maximum_age_hours: float
    age_hours: float
    missing_provenance_fields: tuple[str, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        status = normalize_required_text(
            self.status, field_name="status", uppercase=True,
        )
        if status not in EXTERNAL_CONTEXT_QUALITY_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(EXTERNAL_CONTEXT_QUALITY_STATUSES)
            )
        validate_aware_datetime(self.checked_at, field_name="checked_at")
        maximum_age = _validate_positive_number(
            self.maximum_age_hours, field_name="maximum_age_hours",
        )
        age = _validate_non_negative_number(
            self.age_hours, field_name="age_hours",
        )
        _validate_text_tuple(
            self.missing_provenance_fields,
            field_name="missing_provenance_fields",
        )
        _validate_text_tuple(self.warnings, field_name="warnings")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "maximum_age_hours", maximum_age)
        object.__setattr__(self, "age_hours", round(age, 4))

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at.isoformat(),
            "maximum_age_hours": self.maximum_age_hours,
            "age_hours": self.age_hours,
            "missing_provenance_fields": list(
                self.missing_provenance_fields
            ),
            "warnings": list(self.warnings),
            "is_ready": self.is_ready,
        }


@dataclass(frozen=True, slots=True)
class ExternalContextEvidence:
    """One normalized context record with source and quality evidence."""

    record: ExternalContextRecord
    provenance: ExternalContextProvenance
    quality: ExternalContextQualityAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.record, ExternalContextRecord):
            raise TypeError("record must be an ExternalContextRecord")
        if not isinstance(self.provenance, ExternalContextProvenance):
            raise TypeError("provenance must be ExternalContextProvenance")
        if not isinstance(self.quality, ExternalContextQualityAssessment):
            raise TypeError("quality must be ExternalContextQualityAssessment")
        if self.quality.checked_at < self.provenance.published_at:
            raise ValueError(
                "quality.checked_at must not be earlier than "
                "provenance.published_at"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
        }


class ExternalContextQualityService:
    """Assess context freshness and optional source-lineage completeness."""

    WARNING_STALE = "External context exceeds the configured maximum age"
    WARNING_PARTIAL = "External context provenance is incomplete"

    @classmethod
    def assess(
        cls,
        provenance: ExternalContextProvenance,
        *,
        checked_at: datetime,
        maximum_age_hours: float,
    ) -> ExternalContextQualityAssessment:
        if not isinstance(provenance, ExternalContextProvenance):
            raise TypeError(
                "provenance must be an ExternalContextProvenance"
            )
        validate_aware_datetime(checked_at, field_name="checked_at")
        maximum_age = _validate_positive_number(
            maximum_age_hours, field_name="maximum_age_hours",
        )
        if checked_at < provenance.published_at:
            raise ValueError(
                "checked_at must not be earlier than published_at"
            )
        age_hours = (
            checked_at - provenance.published_at
        ).total_seconds() / 3600.0
        missing_fields = tuple(
            field_name
            for field_name in ("source_url", "checksum_sha256")
            if getattr(provenance, field_name) is None
        )
        if age_hours > maximum_age:
            status = "STALE"
            warnings = (cls.WARNING_STALE,)
            if missing_fields:
                warnings += (cls.WARNING_PARTIAL,)
        elif missing_fields:
            status = "PARTIAL"
            warnings = (cls.WARNING_PARTIAL,)
        else:
            status = "READY"
            warnings = ()
        return ExternalContextQualityAssessment(
            status=status,
            checked_at=checked_at,
            maximum_age_hours=maximum_age,
            age_hours=age_hours,
            missing_provenance_fields=missing_fields,
            warnings=warnings,
        )


def _validate_text_tuple(value: object, *, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field_name} must contain non-empty strings")


def _validate_non_negative_number(value: object, *, field_name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(
            f"{field_name} must be a finite non-negative number"
        )
    return float(value)


def _validate_positive_number(value: object, *, field_name: str) -> float:
    normalized = _validate_non_negative_number(value, field_name=field_name)
    if normalized <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return normalized
