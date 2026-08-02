"""
Market deployment decision models.
"""

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Any


@dataclass(frozen=True, slots=True)
class DeploymentDecision:
    """
    Machine-generated deployment evidence.

    This is not a final investment recommendation. External news,
    macroeconomic, geopolitical, and portfolio-price context must still
    be reviewed before capital is deployed.
    """

    mode: str
    deployment_fraction: float
    confidence: str
    positive_count: int
    neutral_count: int
    negative_count: int
    universe_size: int
    reasons: tuple[str, ...]
    cautions: tuple[str, ...]
    external_context_required: bool = True

    SUPPORTED_MODES = (
        "INVEST_NOW",
        "PARTIAL_DEPLOYMENT",
        "WAIT",
    )
    SUPPORTED_CONFIDENCE = (
        "LOW",
        "MEDIUM",
        "HIGH",
    )

    def __post_init__(self) -> None:
        normalized_mode = self.mode.strip().upper()
        normalized_confidence = (
            self.confidence.strip().upper()
        )

        if normalized_mode not in self.SUPPORTED_MODES:
            raise ValueError(
                "mode must be one of: "
                + ", ".join(self.SUPPORTED_MODES)
            )

        if (
            normalized_confidence
            not in self.SUPPORTED_CONFIDENCE
        ):
            raise ValueError(
                "confidence must be one of: "
                + ", ".join(self.SUPPORTED_CONFIDENCE)
            )

        if (
            isinstance(self.deployment_fraction, bool)
            or not isinstance(
                self.deployment_fraction,
                Real,
            )
            or not isfinite(
                float(self.deployment_fraction)
            )
            or not 0.0
            <= float(self.deployment_fraction)
            <= 1.0
        ):
            raise ValueError(
                "deployment_fraction must be between 0 and 1"
            )

        for field_name in (
            "positive_count",
            "neutral_count",
            "negative_count",
            "universe_size",
        ):
            value = getattr(self, field_name)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            self.positive_count
            + self.neutral_count
            + self.negative_count
            != self.universe_size
        ):
            raise ValueError(
                "recommendation counts must equal universe_size"
            )

        for field_name in (
            "reasons",
            "cautions",
        ):
            values = getattr(self, field_name)

            if not isinstance(values, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if any(
                not isinstance(value, str)
                or not value.strip()
                for value in values
            ):
                raise ValueError(
                    f"{field_name} must contain non-empty strings"
                )

        object.__setattr__(
            self,
            "mode",
            normalized_mode,
        )
        object.__setattr__(
            self,
            "confidence",
            normalized_confidence,
        )

    @property
    def positive_breadth(self) -> float:
        if self.universe_size == 0:
            return 0.0

        return round(
            self.positive_count
            / self.universe_size,
            8,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "deployment_fraction": (
                self.deployment_fraction
            ),
            "deployment_percent": round(
                self.deployment_fraction * 100.0,
                2,
            ),
            "confidence": self.confidence,
            "positive_count": self.positive_count,
            "neutral_count": self.neutral_count,
            "negative_count": self.negative_count,
            "universe_size": self.universe_size,
            "positive_breadth": self.positive_breadth,
            "reasons": list(self.reasons),
            "cautions": list(self.cautions),
            "external_context_required": (
                self.external_context_required
            ),
        }