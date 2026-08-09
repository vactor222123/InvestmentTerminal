"""
Versioned expected archive-cadence policy for historical research continuity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalArchiveCadencePolicy:
    """
    Explicit expected cadence for canonical historical snapshot generation.

    Version 1 intentionally supports only a fixed elapsed interval anchored to
    one timezone-aware GENERATED_AT timestamp. It does not infer business-day,
    exchange-session, holiday, or retry semantics.
    """

    cadence_id: str
    version: int
    timestamp_basis: str
    anchor_at: datetime
    interval_seconds: int

    FIXED_INTERVAL_ID: ClassVar[str] = "FIXED_INTERVAL_ARCHIVE_CADENCE"
    FIXED_INTERVAL_VERSION: ClassVar[int] = 1
    GENERATED_AT: ClassVar[str] = "GENERATED_AT"

    SUPPORTED_TIMESTAMP_BASES: ClassVar[tuple[str, ...]] = (
        GENERATED_AT,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cadence_id",
            normalize_required_text(
                self.cadence_id,
                field_name="cadence_id",
                uppercase=True,
            ),
        )

        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version <= 0
        ):
            raise ValueError(
                "version must be a positive integer"
            )

        object.__setattr__(
            self,
            "timestamp_basis",
            normalize_required_text(
                self.timestamp_basis,
                field_name="timestamp_basis",
                uppercase=True,
            ),
        )
        if self.timestamp_basis not in self.SUPPORTED_TIMESTAMP_BASES:
            raise ValueError(
                "timestamp_basis must be one of: "
                + ", ".join(
                    self.SUPPORTED_TIMESTAMP_BASES
                )
            )

        validate_aware_datetime(
            self.anchor_at,
            field_name="anchor_at",
        )

        if (
            isinstance(self.interval_seconds, bool)
            or not isinstance(self.interval_seconds, int)
            or self.interval_seconds <= 0
        ):
            raise ValueError(
                "interval_seconds must be a positive integer"
            )

        if (
            self.cadence_id == self.FIXED_INTERVAL_ID
            and self.version != self.FIXED_INTERVAL_VERSION
        ):
            raise ValueError(
                "FIXED_INTERVAL_ARCHIVE_CADENCE supports only version 1"
            )

    @classmethod
    def fixed_interval_v1(
        cls,
        *,
        anchor_at: datetime,
        interval_seconds: int,
    ) -> "HistoricalArchiveCadencePolicy":
        return cls(
            cadence_id=cls.FIXED_INTERVAL_ID,
            version=cls.FIXED_INTERVAL_VERSION,
            timestamp_basis=cls.GENERATED_AT,
            anchor_at=anchor_at,
            interval_seconds=interval_seconds,
        )

    @property
    def identity_key(self) -> str:
        return (
            f"{self.cadence_id}@{self.version}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cadence_id": self.cadence_id,
            "version": self.version,
            "identity_key": self.identity_key,
            "timestamp_basis": self.timestamp_basis,
            "anchor_at": self.anchor_at.isoformat(),
            "interval_seconds": self.interval_seconds,
        }
