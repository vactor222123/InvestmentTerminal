"""Provider-independent sentiment evidence for external context."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


EXTERNAL_CONTEXT_SENTIMENT_LABELS = (
    "NEGATIVE",
    "NEUTRAL",
    "POSITIVE",
    "MIXED",
    "UNKNOWN",
)


@dataclass(frozen=True, slots=True)
class ExternalContextSentimentEvidence:
    """One traceable sentiment assessment for a normalized context record."""

    context_id: str
    label: str
    assessed_at: datetime
    method: str
    method_version: str
    score: float | None = None
    confidence: float | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        label = normalize_required_text(
            self.label,
            field_name="label",
            uppercase=True,
        )
        if label not in EXTERNAL_CONTEXT_SENTIMENT_LABELS:
            raise ValueError(
                "label must be one of: "
                + ", ".join(EXTERNAL_CONTEXT_SENTIMENT_LABELS)
            )
        validate_aware_datetime(
            self.assessed_at,
            field_name="assessed_at",
        )
        score = _validate_optional_bounded_number(
            self.score,
            field_name="score",
            minimum=-1.0,
            maximum=1.0,
        )
        confidence = _validate_optional_bounded_number(
            self.confidence,
            field_name="confidence",
            minimum=0.0,
            maximum=1.0,
        )
        if not isinstance(self.reasons, tuple):
            raise TypeError("reasons must be a tuple")
        if any(
            not isinstance(reason, str) or not reason.strip()
            for reason in self.reasons
        ):
            raise ValueError("reasons must contain non-empty strings")
        if label in {"MIXED", "UNKNOWN"} and not self.reasons:
            raise ValueError(
                "reasons must explain MIXED or UNKNOWN sentiment"
            )

        object.__setattr__(self, "context_id", normalize_required_text(
            self.context_id,
            field_name="context_id",
        ))
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "method", normalize_required_text(
            self.method,
            field_name="method",
        ))
        object.__setattr__(self, "method_version", normalize_required_text(
            self.method_version,
            field_name="method_version",
        ))
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "reasons", tuple(
            reason.strip() for reason in self.reasons
        ))

    @property
    def is_quantified(self) -> bool:
        return self.score is not None and self.confidence is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "label": self.label,
            "score": self.score,
            "confidence": self.confidence,
            "assessed_at": self.assessed_at.isoformat(),
            "method": self.method,
            "method_version": self.method_version,
            "reasons": list(self.reasons),
            "is_quantified": self.is_quantified,
        }


def _validate_optional_bounded_number(
    value: object,
    *,
    field_name: str,
    minimum: float,
    maximum: float,
) -> float | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or not minimum <= float(value) <= maximum
    ):
        raise ValueError(
            f"{field_name} must be between {minimum} and {maximum}"
        )
    return float(value)
