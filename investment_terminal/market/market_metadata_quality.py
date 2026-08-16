"""
Source provenance and data-quality contracts for market metadata.
"""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


MARKET_METADATA_QUALITY_STATUSES = (
    "READY",
    "PARTIAL",
    "STALE",
)


@dataclass(frozen=True, slots=True)
class MarketMetadataProvenance:
    """Traceable source lineage for one market-metadata observation."""

    source: str
    observed_at: datetime
    fetched_at: datetime
    source_record_id: str | None = None
    checksum_sha256: str | None = None

    def __post_init__(self) -> None:
        validate_aware_datetime(
            self.observed_at,
            field_name="observed_at",
        )
        validate_aware_datetime(
            self.fetched_at,
            field_name="fetched_at",
        )
        if self.fetched_at < self.observed_at:
            raise ValueError(
                "fetched_at must not be earlier than observed_at"
            )

        checksum = normalize_optional_text(
            self.checksum_sha256,
            field_name="checksum_sha256",
            uppercase=False,
        )
        if checksum is not None:
            checksum = checksum.lower()
            if (
                len(checksum) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in checksum
                )
            ):
                raise ValueError(
                    "checksum_sha256 must contain 64 hexadecimal characters"
                )

        object.__setattr__(
            self,
            "source",
            normalize_required_text(
                self.source,
                field_name="source",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "source_record_id",
            normalize_optional_text(
                self.source_record_id,
                field_name="source_record_id",
            ),
        )
        object.__setattr__(self, "checksum_sha256", checksum)

    @property
    def is_fully_traceable(self) -> bool:
        return (
            self.source_record_id is not None
            and self.checksum_sha256 is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_record_id": self.source_record_id,
            "observed_at": self.observed_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "checksum_sha256": self.checksum_sha256,
            "is_fully_traceable": self.is_fully_traceable,
        }


@dataclass(frozen=True, slots=True)
class MarketMetadataQualityAssessment:
    """Explicit freshness and provenance quality for one metadata record."""

    status: str
    checked_at: datetime
    maximum_age_days: float
    age_days: float
    missing_provenance_fields: tuple[str, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        status = normalize_required_text(
            self.status,
            field_name="status",
            uppercase=True,
        )
        if status not in MARKET_METADATA_QUALITY_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(MARKET_METADATA_QUALITY_STATUSES)
            )
        validate_aware_datetime(
            self.checked_at,
            field_name="checked_at",
        )
        _validate_non_negative_number(
            self.age_days,
            field_name="age_days",
        )
        _validate_positive_number(
            self.maximum_age_days,
            field_name="maximum_age_days",
        )
        _validate_text_tuple(
            self.missing_provenance_fields,
            field_name="missing_provenance_fields",
        )
        _validate_text_tuple(
            self.warnings,
            field_name="warnings",
        )

        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "age_days",
            round(float(self.age_days), 4),
        )
        object.__setattr__(
            self,
            "maximum_age_days",
            float(self.maximum_age_days),
        )

    @property
    def is_ready(self) -> bool:
        return self.status == "READY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at.isoformat(),
            "maximum_age_days": self.maximum_age_days,
            "age_days": self.age_days,
            "missing_provenance_fields": list(
                self.missing_provenance_fields
            ),
            "warnings": list(self.warnings),
            "is_ready": self.is_ready,
        }


class MarketMetadataQualityService:
    """Assess provenance completeness and observation freshness."""

    WARNING_STALE = (
        "Market metadata observation exceeds the configured maximum age"
    )
    WARNING_PARTIAL = (
        "Market metadata provenance is incomplete"
    )

    @classmethod
    def assess(
        cls,
        provenance: MarketMetadataProvenance,
        *,
        checked_at: datetime,
        maximum_age_days: float,
    ) -> MarketMetadataQualityAssessment:
        if not isinstance(provenance, MarketMetadataProvenance):
            raise TypeError(
                "provenance must be a MarketMetadataProvenance"
            )
        validate_aware_datetime(
            checked_at,
            field_name="checked_at",
        )
        maximum_age = _validate_positive_number(
            maximum_age_days,
            field_name="maximum_age_days",
        )
        if checked_at < provenance.observed_at:
            raise ValueError(
                "checked_at must not be earlier than observed_at"
            )

        age_days = (
            checked_at - provenance.observed_at
        ).total_seconds() / 86400.0
        missing_fields = tuple(
            field_name
            for field_name in (
                "source_record_id",
                "checksum_sha256",
            )
            if getattr(provenance, field_name) is None
        )

        if age_days > maximum_age:
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

        return MarketMetadataQualityAssessment(
            status=status,
            checked_at=checked_at,
            maximum_age_days=maximum_age,
            age_days=age_days,
            missing_provenance_fields=missing_fields,
            warnings=warnings,
        )


def _validate_positive_number(
    value: object,
    *,
    field_name: str,
) -> float:
    normalized = _validate_non_negative_number(
        value,
        field_name=field_name,
    )
    if normalized <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return normalized


def _validate_non_negative_number(
    value: object,
    *,
    field_name: str,
) -> float:
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


def _validate_text_tuple(
    value: object,
    *,
    field_name: str,
) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field_name} must be a tuple")
    if any(
        not isinstance(item, str)
        or not item.strip()
        for item in value
    ):
        raise ValueError(
            f"{field_name} must contain non-empty strings"
        )
