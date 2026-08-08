"""
Canonical immutable contracts for safe historical replay.
"""

import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar, Mapping

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalReplayRequest:
    """Request one explicit historical replay representation."""

    snapshot_id: str
    mode: str

    EXACT_ARCHIVED_PACKAGE: ClassVar[str] = (
        "EXACT_ARCHIVED_PACKAGE"
    )
    NORMALIZED_HISTORICAL_VIEW: ClassVar[str] = (
        "NORMALIZED_HISTORICAL_VIEW"
    )
    CURRENT_CODE_RECALCULATION: ClassVar[str] = (
        "CURRENT_CODE_RECALCULATION"
    )

    SUPPORTED_MODES: ClassVar[tuple[str, ...]] = (
        EXACT_ARCHIVED_PACKAGE,
        NORMALIZED_HISTORICAL_VIEW,
    )
    DEFINED_MODES: ClassVar[tuple[str, ...]] = (
        EXACT_ARCHIVED_PACKAGE,
        NORMALIZED_HISTORICAL_VIEW,
        CURRENT_CODE_RECALCULATION,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )

        normalized_mode = normalize_required_text(
            self.mode,
            field_name="mode",
            uppercase=True,
        )

        if normalized_mode not in self.DEFINED_MODES:
            raise ValueError(
                "mode must be one of: "
                + ", ".join(
                    self.DEFINED_MODES
                )
            )

        object.__setattr__(
            self,
            "mode",
            normalized_mode,
        )

    @property
    def is_supported(
        self,
    ) -> bool:
        """Return whether Sprint 13 implements this replay mode."""
        return self.mode in self.SUPPORTED_MODES

    @property
    def is_exact_evidence_request(
        self,
    ) -> bool:
        return self.mode == self.EXACT_ARCHIVED_PACKAGE

    def to_dict(
        self,
    ) -> dict[str, str | bool]:
        return {
            "snapshot_id": self.snapshot_id,
            "mode": self.mode,
            "supported": self.is_supported,
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayResult:
    """
    Immutable replay result with explicit historical evidence provenance.

    `payload` is the requested representation. The evidence checksum always
    identifies the immutable archived Review Package that anchors the result.
    """

    snapshot_id: str
    mode: str
    package_schema_version: str
    evidence_checksum_sha256: str
    payload: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )

        normalized_mode = normalize_required_text(
            self.mode,
            field_name="mode",
            uppercase=True,
        )

        if normalized_mode not in HistoricalReplayRequest.SUPPORTED_MODES:
            raise ValueError(
                "HistoricalReplayResult supports only implemented replay "
                "modes: "
                + ", ".join(
                    HistoricalReplayRequest.SUPPORTED_MODES
                )
            )

        object.__setattr__(
            self,
            "mode",
            normalized_mode,
        )
        object.__setattr__(
            self,
            "package_schema_version",
            normalize_required_text(
                self.package_schema_version,
                field_name="package_schema_version",
            ),
        )
        object.__setattr__(
            self,
            "evidence_checksum_sha256",
            HistoricalSnapshot._normalize_sha256(
                self.evidence_checksum_sha256
            ),
        )
        object.__setattr__(
            self,
            "payload",
            self._normalize_payload(
                self.payload
            ),
        )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(
                normalize_required_text(
                    warning,
                    field_name="warning",
                )
                for warning in self.warnings
            ),
        )

    @property
    def is_exact_archived_evidence(
        self,
    ) -> bool:
        return (
            self.mode
            == HistoricalReplayRequest.EXACT_ARCHIVED_PACKAGE
        )

    @property
    def is_normalized_view(
        self,
    ) -> bool:
        return (
            self.mode
            == HistoricalReplayRequest.NORMALIZED_HISTORICAL_VIEW
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "mode": self.mode,
            "package_schema_version": self.package_schema_version,
            "evidence_checksum_sha256": (
                self.evidence_checksum_sha256
            ),
            "exact_archived_evidence": (
                self.is_exact_archived_evidence
            ),
            "warnings": list(
                self.warnings
            ),
            "payload": self._thaw_json_value(
                self.payload
            ),
        }

    @classmethod
    def _normalize_payload(
        cls,
        value: object,
    ) -> Mapping[str, Any]:
        if not isinstance(
            value,
            Mapping,
        ):
            raise ValueError(
                "payload must be a JSON object"
            )

        try:
            serialized = json.dumps(
                dict(
                    value
                ),
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
                allow_nan=False,
            )
            normalized = json.loads(
                serialized
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "payload must contain JSON-compatible values"
            ) from exc

        if not isinstance(
            normalized,
            dict,
        ):
            raise ValueError(
                "payload must be a JSON object"
            )

        return cls._freeze_json_value(
            normalized
        )

    @classmethod
    def _freeze_json_value(
        cls,
        value: Any,
    ) -> Any:
        if isinstance(
            value,
            dict,
        ):
            return MappingProxyType(
                {
                    key: cls._freeze_json_value(
                        item
                    )
                    for key, item in value.items()
                }
            )

        if isinstance(
            value,
            list,
        ):
            return tuple(
                cls._freeze_json_value(
                    item
                )
                for item in value
            )

        return value

    @classmethod
    def _thaw_json_value(
        cls,
        value: Any,
    ) -> Any:
        if isinstance(
            value,
            Mapping,
        ):
            return {
                key: cls._thaw_json_value(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            tuple,
        ):
            return [
                cls._thaw_json_value(
                    item
                )
                for item in value
            ]

        return value
