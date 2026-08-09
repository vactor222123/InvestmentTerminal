"""
Explicit claim boundary for historical outcome research.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_sample_sufficiency import (
    HistoricalOutcomeSampleAssessment,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeResearchClaimAssessment:
    """Machine-readable boundary for what one research result may claim."""

    claim_policy: str
    sample_status: str
    descriptive_claims_allowed: bool
    comparative_claims_allowed: bool
    predictive_claims_allowed: bool
    causal_claims_allowed: bool
    effectiveness_claims_allowed: bool
    warning: str

    DESCRIPTIVE_ONLY: ClassVar[str] = "DESCRIPTIVE_ONLY"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim_policy",
            normalize_required_text(
                self.claim_policy,
                field_name="claim_policy",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "sample_status",
            normalize_required_text(
                self.sample_status,
                field_name="sample_status",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "warning",
            normalize_required_text(
                self.warning,
                field_name="warning",
            ),
        )

        if self.claim_policy != self.DESCRIPTIVE_ONLY:
            raise ValueError(
                f"unsupported claim policy: {self.claim_policy}"
            )
        if self.sample_status not in {
            HistoricalOutcomeSampleAssessment.INSUFFICIENT,
            HistoricalOutcomeSampleAssessment.SUFFICIENT,
        }:
            raise ValueError(
                f"unsupported sample status: {self.sample_status}"
            )

        if any(
            (
                self.comparative_claims_allowed,
                self.predictive_claims_allowed,
                self.causal_claims_allowed,
                self.effectiveness_claims_allowed,
            )
        ):
            raise ValueError(
                "DESCRIPTIVE_ONLY must not allow comparative, predictive, "
                "causal, or effectiveness claims"
            )

        expected_descriptive = (
            self.sample_status
            == HistoricalOutcomeSampleAssessment.SUFFICIENT
        )
        if self.descriptive_claims_allowed != expected_descriptive:
            raise ValueError(
                "descriptive_claims_allowed must match sample sufficiency"
            )

    @property
    def claims_restricted_by_sample_size(self) -> bool:
        return (
            self.sample_status
            == HistoricalOutcomeSampleAssessment.INSUFFICIENT
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_policy": self.claim_policy,
            "sample_status": self.sample_status,
            "descriptive_claims_allowed": self.descriptive_claims_allowed,
            "comparative_claims_allowed": self.comparative_claims_allowed,
            "predictive_claims_allowed": self.predictive_claims_allowed,
            "causal_claims_allowed": self.causal_claims_allowed,
            "effectiveness_claims_allowed": self.effectiveness_claims_allowed,
            "claims_restricted_by_sample_size": (
                self.claims_restricted_by_sample_size
            ),
            "warning": self.warning,
        }


class HistoricalOutcomeResearchClaimBoundaryService:
    """
    Enforce the Sprint 16 descriptive-only research claim boundary.

    Sufficient samples may be described statistically, but they still do not
    authorize comparative superiority, prediction, causality, recommendation
    effectiveness, success rate, or confidence-of-success claims.

    Insufficient samples remain reportable as observations/coverage, but even
    descriptive aggregate claims are withheld as research conclusions.
    """

    SUFFICIENT_WARNING = (
        "Descriptive historical sample only; do not interpret price movement "
        "as recommendation effectiveness, predictive confidence, or causality"
    )
    INSUFFICIENT_WARNING = (
        "Insufficient eligible sample for descriptive research claims; report "
        "observations, coverage, and sample shortfall without drawing a "
        "research conclusion"
    )

    def assess(
        self,
        *,
        protocol: HistoricalOutcomeResearchProtocol,
        sample_assessment: HistoricalOutcomeSampleAssessment,
    ) -> HistoricalOutcomeResearchClaimAssessment:
        if not isinstance(
            protocol,
            HistoricalOutcomeResearchProtocol,
        ):
            raise TypeError(
                "protocol must be a HistoricalOutcomeResearchProtocol"
            )
        if not isinstance(
            sample_assessment,
            HistoricalOutcomeSampleAssessment,
        ):
            raise TypeError(
                "sample_assessment must be a HistoricalOutcomeSampleAssessment"
            )

        if (
            protocol.claim_policy
            != HistoricalOutcomeResearchProtocol.DESCRIPTIVE_ONLY
        ):
            raise ValueError(
                "unsupported research claim policy: "
                f"{protocol.claim_policy}"
            )

        sufficient = sample_assessment.sufficient

        return HistoricalOutcomeResearchClaimAssessment(
            claim_policy=protocol.claim_policy,
            sample_status=sample_assessment.status,
            descriptive_claims_allowed=sufficient,
            comparative_claims_allowed=False,
            predictive_claims_allowed=False,
            causal_claims_allowed=False,
            effectiveness_claims_allowed=False,
            warning=(
                self.SUFFICIENT_WARNING
                if sufficient
                else self.INSUFFICIENT_WARNING
            ),
        )
