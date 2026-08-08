"""
Canonical typed model for historical timeline events.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalTimelineEvent:
    """Immutable typed representation of one historical timeline row."""

    event_id: int
    snapshot_id: str
    event_type: str
    occurred_at: datetime
    subject_key: str | None
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.event_id, int)
            or isinstance(self.event_id, bool)
            or self.event_id <= 0
        ):
            raise ValueError(
                "event_id must be a positive integer"
            )

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
            "event_type",
            normalize_required_text(
                self.event_type,
                field_name="event_type",
                uppercase=True,
            ),
        )

        validate_aware_datetime(
            self.occurred_at,
            field_name="occurred_at",
        )

        object.__setattr__(
            self,
            "subject_key",
            normalize_optional_text(
                self.subject_key,
                field_name="subject_key",
            ),
        )
        object.__setattr__(
            self,
            "payload",
            self._normalize_payload(
                self.payload
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Return the stable JSON-ready event contract."""
        return {
            "event_id": self.event_id,
            "snapshot_id": self.snapshot_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "subject_key": self.subject_key,
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
                dict(value),
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
