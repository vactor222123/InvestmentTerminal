"""
Canonical models for immutable historical review snapshots.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalSnapshot:
    """Immutable metadata describing one archived review package."""

    snapshot_id: str
    package_schema_version: str
    generated_at: datetime
    archived_at: datetime
    relative_path: str
    checksum_sha256: str
    package_id: str | None = None
    product_version: str | None = None
    supersedes: str | None = None
    status: str = "ARCHIVED"

    SUPPORTED_STATUSES = (
        "ARCHIVED",
        "VERIFIED",
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            self._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "package_schema_version",
            normalize_required_text(
                self.package_schema_version,
                field_name="package_schema_version",
            ),
        )

        validate_aware_datetime(
            self.generated_at,
            field_name="generated_at",
        )
        validate_aware_datetime(
            self.archived_at,
            field_name="archived_at",
        )

        if self.archived_at < self.generated_at:
            raise ValueError(
                "archived_at must not be earlier than generated_at"
            )

        object.__setattr__(
            self,
            "relative_path",
            self._normalize_relative_path(
                self.relative_path
            ),
        )
        object.__setattr__(
            self,
            "checksum_sha256",
            self._normalize_sha256(
                self.checksum_sha256
            ),
        )
        object.__setattr__(
            self,
            "package_id",
            normalize_optional_text(
                self.package_id,
                field_name="package_id",
            ),
        )
        object.__setattr__(
            self,
            "product_version",
            normalize_optional_text(
                self.product_version,
                field_name="product_version",
            ),
        )
        object.__setattr__(
            self,
            "supersedes",
            self._normalize_optional_uuid(
                self.supersedes,
                field_name="supersedes",
            ),
        )
        object.__setattr__(
            self,
            "status",
            self._normalize_status(
                self.status
            ),
        )

        if self.supersedes == self.snapshot_id:
            raise ValueError(
                "supersedes must not reference snapshot_id"
            )

    def to_dict(self) -> dict[str, Any]:
        """Return the stable JSON-ready snapshot metadata contract."""
        return {
            "snapshot_id": self.snapshot_id,
            "package_id": self.package_id,
            "package_schema_version": self.package_schema_version,
            "product_version": self.product_version,
            "generated_at": self.generated_at.isoformat(),
            "archived_at": self.archived_at.isoformat(),
            "relative_path": self.relative_path,
            "checksum_sha256": self.checksum_sha256,
            "supersedes": self.supersedes,
            "status": self.status,
        }

    @staticmethod
    def _normalize_uuid(
        value: object,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a valid UUID string"
            )

        try:
            parsed = UUID(
                value.strip()
            )
        except (
            AttributeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"{field_name} must be a valid UUID string"
            ) from exc

        return str(parsed)

    @classmethod
    def _normalize_optional_uuid(
        cls,
        value: object,
        *,
        field_name: str,
    ) -> str | None:
        if value is None:
            return None

        return cls._normalize_uuid(
            value,
            field_name=field_name,
        )

    @staticmethod
    def _normalize_relative_path(
        value: object,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "relative_path must be a non-empty string"
            )

        normalized_input = (
            value.strip()
            .replace("\\", "/")
        )
        path = PurePosixPath(
            normalized_input
        )

        if path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )

        if ".." in path.parts:
            raise ValueError(
                "relative_path must not escape the archive root"
            )

        if path.suffix.lower() != ".json":
            raise ValueError(
                "relative_path must point to a JSON file"
            )

        normalized = path.as_posix()

        if normalized in (
            ".",
            "",
        ):
            raise ValueError(
                "relative_path must identify a file"
            )

        return normalized

    @staticmethod
    def _normalize_sha256(
        value: object,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                "checksum_sha256 must contain 64 hexadecimal characters"
            )

        normalized = value.strip().lower()

        if (
            len(normalized) != 64
            or any(
                character not in "0123456789abcdef"
                for character in normalized
            )
        ):
            raise ValueError(
                "checksum_sha256 must contain 64 hexadecimal characters"
            )

        return normalized

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
