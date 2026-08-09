"""
Structural compatibility assessment for historical outcome methodologies.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalMethodologyCompatibility:
    """
    Structural compatibility between two outcome methodologies.

    This model describes methodology similarity only. It does not imply
    statistical comparability, recommendation effectiveness, or causal validity.
    """

    status: str
    left_identity: str
    right_identity: str
    reasons: tuple[str, ...]

    COMPATIBLE: ClassVar[str] = "COMPATIBLE"
    PARTIALLY_COMPATIBLE: ClassVar[str] = "PARTIALLY_COMPATIBLE"
    INCOMPATIBLE: ClassVar[str] = "INCOMPATIBLE"

    SUPPORTED_STATUSES: ClassVar[tuple[str, ...]] = (
        COMPATIBLE,
        PARTIALLY_COMPATIBLE,
        INCOMPATIBLE,
    )

    def __post_init__(self) -> None:
        normalized = normalize_required_text(
            self.status,
            field_name="status",
            uppercase=True,
        )
        if normalized not in self.SUPPORTED_STATUSES:
            raise ValueError(
                "unsupported methodology compatibility status"
            )
        object.__setattr__(self, "status", normalized)

        for field_name in (
            "left_identity",
            "right_identity",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                    uppercase=True,
                ),
            )

        if not isinstance(self.reasons, tuple):
            raise TypeError(
                "reasons must be a tuple"
            )

        object.__setattr__(
            self,
            "reasons",
            tuple(
                normalize_required_text(
                    reason,
                    field_name="reason",
                )
                for reason in self.reasons
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "left_identity": self.left_identity,
            "right_identity": self.right_identity,
            "reasons": list(self.reasons),
            "semantics": (
                "Structural methodology compatibility only; not statistical "
                "comparability, recommendation effectiveness, or causality"
            ),
        }


class HistoricalMethodologyCompatibilityService:
    """
    Assess structural compatibility between two explicit methodologies.
    """

    def assess(
        self,
        *,
        left: HistoricalOutcomeMethodology,
        right: HistoricalOutcomeMethodology,
    ) -> HistoricalMethodologyCompatibility:
        if not isinstance(left, HistoricalOutcomeMethodology):
            raise TypeError(
                "left must be a HistoricalOutcomeMethodology"
            )
        if not isinstance(right, HistoricalOutcomeMethodology):
            raise TypeError(
                "right must be a HistoricalOutcomeMethodology"
            )

        if left.identity_key == right.identity_key:
            return HistoricalMethodologyCompatibility(
                status=HistoricalMethodologyCompatibility.COMPATIBLE,
                left_identity=left.identity_key,
                right_identity=right.identity_key,
                reasons=("Methodology identity is identical",),
            )

        reasons: list[str] = []

        if left.window_kind != right.window_kind:
            reasons.append(
                "Observation window kinds differ"
            )

        if (
            left.evidence_selection_policy.price_field
            != right.evidence_selection_policy.price_field
        ):
            reasons.append(
                "Price fields differ"
            )

        if reasons:
            return HistoricalMethodologyCompatibility(
                status=HistoricalMethodologyCompatibility.INCOMPATIBLE,
                left_identity=left.identity_key,
                right_identity=right.identity_key,
                reasons=tuple(reasons),
            )

        if (
            left.endpoint_policy.identity_key
            != right.endpoint_policy.identity_key
        ):
            reasons.append(
                "Endpoint policies differ"
            )

        if (
            left.evidence_selection_policy.identity_key
            != right.evidence_selection_policy.identity_key
        ):
            reasons.append(
                "Evidence-selection policies differ"
            )

        if left.version != right.version:
            reasons.append(
                "Methodology versions differ"
            )

        if not reasons:
            reasons.append(
                "Methodology identifiers differ despite matching structural contracts"
            )

        return HistoricalMethodologyCompatibility(
            status=HistoricalMethodologyCompatibility.PARTIALLY_COMPATIBLE,
            left_identity=left.identity_key,
            right_identity=right.identity_key,
            reasons=tuple(reasons),
        )
