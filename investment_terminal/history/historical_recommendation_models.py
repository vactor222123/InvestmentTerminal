"""
Canonical read model for one normalized historical recommendation.
"""

import json
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalRecommendation:
    """Immutable normalized recommendation projection for one snapshot."""

    snapshot_id: str
    recommendation_key: str
    symbol: str | None
    action: str | None
    score: float | None
    confidence: float | None
    rationale: str | None
    payload: Mapping[str, Any]

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
            "recommendation_key",
            normalize_required_text(
                self.recommendation_key,
                field_name="recommendation_key",
            ),
        )

        for field_name in (
            "symbol",
            "action",
            "rationale",
        ):
            normalized = normalize_optional_text(
                getattr(
                    self,
                    field_name,
                ),
                field_name=field_name,
            )
            if (
                normalized is not None
                and field_name in (
                    "symbol",
                    "action",
                )
            ):
                normalized = normalized.upper()

            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        for field_name in (
            "score",
            "confidence",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is None:
                continue

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    (
                        int,
                        float,
                    ),
                )
                or not isfinite(
                    float(
                        value
                    )
                )
            ):
                raise ValueError(
                    f"{field_name} must be a finite number or None"
                )

            object.__setattr__(
                self,
                field_name,
                float(
                    value
                ),
            )

        object.__setattr__(
            self,
            "payload",
            self._normalize_payload(
                self.payload
            ),
        )

    def comparison_payload(
        self,
    ) -> dict[str, Any]:
        """Return descriptive data embedded in RecommendationChange."""
        return {
            "symbol": self.symbol,
            "action": self.action,
            "rationale": self.rationale,
            "payload": self._thaw_json_value(
                self.payload
            ),
        }

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "recommendation_key": self.recommendation_key,
            "symbol": self.symbol,
            "action": self.action,
            "score": self.score,
            "confidence": self.confidence,
            "rationale": self.rationale,
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
            encoded = json.dumps(
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
                encoded
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
