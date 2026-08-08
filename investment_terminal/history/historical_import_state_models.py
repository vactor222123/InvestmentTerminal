"""
Canonical model for historical snapshot import state.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalImportState:
    """Immutable state of structured import for one historical snapshot."""

    snapshot_id: str
    status: str
    metadata_synchronized_at: datetime
    updated_at: datetime
    package_verified_at: datetime | None = None
    details_imported_at: datetime | None = None
    timeline_built_at: datetime | None = None
    importer_version: str | None = None
    failure_reason: str | None = None

    SUPPORTED_STATUSES: ClassVar[tuple[str, ...]] = (
        "METADATA_ONLY",
        "VERIFIED",
        "IMPORTING",
        "IMPORTED",
        "FAILED",
    )
    ALLOWED_TRANSITIONS: ClassVar[
        dict[str, tuple[str, ...]]
    ] = {
        "METADATA_ONLY": (
            "VERIFIED",
            "FAILED",
        ),
        "VERIFIED": (
            "IMPORTING",
            "FAILED",
        ),
        "IMPORTING": (
            "IMPORTED",
            "FAILED",
        ),
        "IMPORTED": (),
        "FAILED": (
            "VERIFIED",
        ),
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "status",
            self._normalize_status(
                self.status
            ),
        )

        validate_aware_datetime(
            self.metadata_synchronized_at,
            field_name="metadata_synchronized_at",
        )
        validate_aware_datetime(
            self.updated_at,
            field_name="updated_at",
        )

        for field_name in (
            "package_verified_at",
            "details_imported_at",
            "timeline_built_at",
        ):
            value = getattr(
                self,
                field_name,
            )
            if value is not None:
                validate_aware_datetime(
                    value,
                    field_name=field_name,
                )

        object.__setattr__(
            self,
            "importer_version",
            normalize_optional_text(
                self.importer_version,
                field_name="importer_version",
            ),
        )
        object.__setattr__(
            self,
            "failure_reason",
            normalize_optional_text(
                self.failure_reason,
                field_name="failure_reason",
            ),
        )

        if self.updated_at < self.metadata_synchronized_at:
            raise ValueError(
                "updated_at must not be earlier than metadata_synchronized_at"
            )

        for field_name in (
            "package_verified_at",
            "details_imported_at",
            "timeline_built_at",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                value is not None
                and value < self.metadata_synchronized_at
            ):
                raise ValueError(
                    f"{field_name} must not be earlier than "
                    "metadata_synchronized_at"
                )

            if (
                value is not None
                and value > self.updated_at
            ):
                raise ValueError(
                    f"{field_name} must not be later than updated_at"
                )

        if (
            self.status in (
                "VERIFIED",
                "IMPORTING",
                "IMPORTED",
            )
            and self.package_verified_at is None
        ):
            raise ValueError(
                f"{self.status} requires package_verified_at"
            )

        if self.status == "IMPORTED":
            if self.details_imported_at is None:
                raise ValueError(
                    "IMPORTED requires details_imported_at"
                )
            if self.timeline_built_at is None:
                raise ValueError(
                    "IMPORTED requires timeline_built_at"
                )

        if (
            self.status == "FAILED"
            and self.failure_reason is None
        ):
            raise ValueError(
                "FAILED requires failure_reason"
            )

        if (
            self.status != "FAILED"
            and self.failure_reason is not None
        ):
            raise ValueError(
                "failure_reason is only valid for FAILED state"
            )

    def can_transition_to(
        self,
        status: str,
    ) -> bool:
        """Return whether one forward state transition is allowed."""
        normalized = self._normalize_status(
            status
        )
        return normalized in self.ALLOWED_TRANSITIONS[
            self.status
        ]

    def require_transition_to(
        self,
        status: str,
    ) -> str:
        """Normalize and require one valid state transition."""
        normalized = self._normalize_status(
            status
        )

        if normalized not in self.ALLOWED_TRANSITIONS[
            self.status
        ]:
            raise ValueError(
                "Historical import state transition is not allowed: "
                f"{self.status} -> {normalized}"
            )

        return normalized

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Return the stable JSON-ready import-state contract."""
        return {
            "snapshot_id": self.snapshot_id,
            "status": self.status,
            "metadata_synchronized_at": (
                self.metadata_synchronized_at.isoformat()
            ),
            "package_verified_at": (
                None
                if self.package_verified_at is None
                else self.package_verified_at.isoformat()
            ),
            "details_imported_at": (
                None
                if self.details_imported_at is None
                else self.details_imported_at.isoformat()
            ),
            "timeline_built_at": (
                None
                if self.timeline_built_at is None
                else self.timeline_built_at.isoformat()
            ),
            "importer_version": self.importer_version,
            "failure_reason": self.failure_reason,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def _normalize_status(
        cls,
        value: object,
    ) -> str:
        normalized = normalize_required_text(
            value,
            field_name="status",
            uppercase=True,
        )

        if normalized not in cls.SUPPORTED_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(
                    cls.SUPPORTED_STATUSES
                )
            )

        return normalized
