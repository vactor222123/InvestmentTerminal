"""
Canonical read model for one normalized historical deployment record.
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
class HistoricalDeployment:
    """Immutable normalized deployment projection for one historical snapshot."""

    snapshot_id: str
    deployment_key: str
    amount: float | None
    share: float | None
    reason: str | None
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
            "deployment_key",
            normalize_required_text(
                self.deployment_key,
                field_name="deployment_key",
            ),
        )
        object.__setattr__(
            self,
            "reason",
            normalize_optional_text(
                self.reason,
                field_name="reason",
            ),
        )

        if self.amount is not None:
            if (
                isinstance(
                    self.amount,
                    bool,
                )
                or not isinstance(
                    self.amount,
                    (
                        int,
                        float,
                    ),
                )
                or not isfinite(
                    float(
                        self.amount
                    )
                )
                or float(
                    self.amount
                ) < 0.0
            ):
                raise ValueError(
                    "amount must be a finite non-negative number or None"
                )

            object.__setattr__(
                self,
                "amount",
                float(
                    self.amount
                ),
            )

        if self.share is not None:
            if (
                isinstance(
                    self.share,
                    bool,
                )
                or not isinstance(
                    self.share,
                    (
                        int,
                        float,
                    ),
                )
                or not isfinite(
                    float(
                        self.share
                    )
                )
                or not 0.0
                <= float(
                    self.share
                )
                <= 1.0
            ):
                raise ValueError(
                    "share must be between 0 and 1 or None"
                )

            object.__setattr__(
                self,
                "share",
                float(
                    self.share
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
        """Return descriptive data embedded in DeploymentChange."""
        return {
            "reason": self.reason,
            "payload": self._thaw_json_value(
                self.payload
            ),
        }

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "deployment_key": self.deployment_key,
            "amount": self.amount,
            "share": self.share,
            "reason": self.reason,
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
