"""
Canonical immutable models for historical recommendation state transitions.
"""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, ClassVar

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


def _normalize_optional_number(
    value: object,
    *,
    field_name: str,
) -> float | None:
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
    ):
        raise ValueError(
            f"{field_name} must be a finite number or None"
        )

    return float(value)


@dataclass(frozen=True, slots=True)
class HistoricalRecommendationState:
    """
    One recommendation state observed at one historical snapshot.

    `present=False` represents an explicit absence of the stable recommendation
    key at that snapshot. Price outcome semantics do not belong here.
    """

    snapshot_id: str
    generated_at: datetime
    recommendation_key: str
    present: bool
    symbol: str | None = None
    action: str | None = None
    score: float | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.snapshot_id,
                field_name="snapshot_id",
            ),
        )
        validate_aware_datetime(
            self.generated_at,
            field_name="generated_at",
        )
        object.__setattr__(
            self,
            "recommendation_key",
            normalize_required_text(
                self.recommendation_key,
                field_name="recommendation_key",
            ),
        )

        if not isinstance(self.present, bool):
            raise TypeError(
                "present must be a bool"
            )

        object.__setattr__(
            self,
            "symbol",
            normalize_optional_text(
                self.symbol,
                field_name="symbol",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "action",
            normalize_optional_text(
                self.action,
                field_name="action",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "score",
            _normalize_optional_number(
                self.score,
                field_name="score",
            ),
        )
        object.__setattr__(
            self,
            "confidence",
            _normalize_optional_number(
                self.confidence,
                field_name="confidence",
            ),
        )

        if not self.present and any(
            value is not None
            for value in (
                self.symbol,
                self.action,
                self.score,
                self.confidence,
            )
        ):
            raise ValueError(
                "absent recommendation state must not contain recommendation values"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at.isoformat(),
            "recommendation_key": self.recommendation_key,
            "present": self.present,
            "symbol": self.symbol,
            "action": self.action,
            "score": self.score,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class HistoricalRecommendationTransition:
    """
    One chronological transition for a stable recommendation key.

    The transition is descriptive only. It does not classify investment
    success, calculate price movement, or infer causality.
    """

    recommendation_key: str
    transition_type: str
    previous: HistoricalRecommendationState | None
    current: HistoricalRecommendationState
    duration_seconds: float | None

    FIRST_OBSERVED: ClassVar[str] = "FIRST_OBSERVED"
    ACTION_CHANGED: ClassVar[str] = "ACTION_CHANGED"
    METRICS_CHANGED: ClassVar[str] = "METRICS_CHANGED"
    DESCRIPTIVE_CHANGED: ClassVar[str] = "DESCRIPTIVE_CHANGED"
    DISAPPEARED: ClassVar[str] = "DISAPPEARED"
    REAPPEARED: ClassVar[str] = "REAPPEARED"
    UNCHANGED: ClassVar[str] = "UNCHANGED"

    SUPPORTED_TYPES: ClassVar[tuple[str, ...]] = (
        FIRST_OBSERVED,
        ACTION_CHANGED,
        METRICS_CHANGED,
        DESCRIPTIVE_CHANGED,
        DISAPPEARED,
        REAPPEARED,
        UNCHANGED,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recommendation_key",
            normalize_required_text(
                self.recommendation_key,
                field_name="recommendation_key",
            ),
        )

        normalized_type = normalize_required_text(
            self.transition_type,
            field_name="transition_type",
            uppercase=True,
        )
        if normalized_type not in self.SUPPORTED_TYPES:
            raise ValueError(
                "transition_type must be one of: "
                + ", ".join(self.SUPPORTED_TYPES)
            )
        object.__setattr__(
            self,
            "transition_type",
            normalized_type,
        )

        if (
            self.previous is not None
            and not isinstance(
                self.previous,
                HistoricalRecommendationState,
            )
        ):
            raise TypeError(
                "previous must be a HistoricalRecommendationState or None"
            )

        if not isinstance(
            self.current,
            HistoricalRecommendationState,
        ):
            raise TypeError(
                "current must be a HistoricalRecommendationState"
            )

        if self.current.recommendation_key != self.recommendation_key:
            raise ValueError(
                "current recommendation_key must match transition recommendation_key"
            )

        if (
            self.previous is not None
            and self.previous.recommendation_key
            != self.recommendation_key
        ):
            raise ValueError(
                "previous recommendation_key must match transition recommendation_key"
            )

        if self.previous is None:
            if self.transition_type != self.FIRST_OBSERVED:
                raise ValueError(
                    "transition without previous state must be FIRST_OBSERVED"
                )
            if not self.current.present:
                raise ValueError(
                    "FIRST_OBSERVED current state must be present"
                )
            if self.duration_seconds is not None:
                raise ValueError(
                    "FIRST_OBSERVED duration_seconds must be None"
                )
            return

        if self.current.generated_at <= self.previous.generated_at:
            raise ValueError(
                "current generated_at must be later than previous generated_at"
            )

        expected_duration = (
            self.current.generated_at
            - self.previous.generated_at
        ).total_seconds()

        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(
                self.duration_seconds,
                (int, float),
            )
            or not isfinite(
                float(self.duration_seconds)
            )
            or float(self.duration_seconds) < 0
        ):
            raise ValueError(
                "duration_seconds must be a finite non-negative number"
            )

        if float(self.duration_seconds) != expected_duration:
            raise ValueError(
                "duration_seconds must match the state timestamps"
            )

        self._validate_transition_semantics()

    def _validate_transition_semantics(
        self,
    ) -> None:
        assert self.previous is not None

        previous = self.previous
        current = self.current

        if self.transition_type == self.DISAPPEARED:
            if not previous.present or current.present:
                raise ValueError(
                    "DISAPPEARED requires present previous and absent current state"
                )
            return

        if self.transition_type == self.REAPPEARED:
            if previous.present or not current.present:
                raise ValueError(
                    "REAPPEARED requires absent previous and present current state"
                )
            return

        if not previous.present or not current.present:
            raise ValueError(
                f"{self.transition_type} requires present previous and current states"
            )

        action_changed = previous.action != current.action
        metrics_changed = (
            previous.score != current.score
            or previous.confidence != current.confidence
        )
        descriptive_changed = previous.symbol != current.symbol

        if self.transition_type == self.ACTION_CHANGED:
            if not action_changed:
                raise ValueError(
                    "ACTION_CHANGED requires action to differ"
                )
            return

        if self.transition_type == self.METRICS_CHANGED:
            if action_changed or not metrics_changed:
                raise ValueError(
                    "METRICS_CHANGED requires unchanged action and changed score/confidence"
                )
            return

        if self.transition_type == self.DESCRIPTIVE_CHANGED:
            if (
                action_changed
                or metrics_changed
                or not descriptive_changed
            ):
                raise ValueError(
                    "DESCRIPTIVE_CHANGED requires unchanged action/metrics and changed symbol"
                )
            return

        if self.transition_type == self.UNCHANGED:
            if (
                action_changed
                or metrics_changed
                or descriptive_changed
            ):
                raise ValueError(
                    "UNCHANGED requires equivalent recommendation state"
                )
            return

        raise ValueError(
            "FIRST_OBSERVED is only valid without a previous state"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "recommendation_key": self.recommendation_key,
            "transition_type": self.transition_type,
            "previous": (
                None
                if self.previous is None
                else self.previous.to_dict()
            ),
            "current": self.current.to_dict(),
            "duration_seconds": self.duration_seconds,
        }
