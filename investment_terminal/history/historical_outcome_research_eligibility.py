"""
Explicit research eligibility assessment for methodology-aware outcomes.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeEligibilityAssessment:
    """One explicit eligibility decision with a stable exclusion reason."""

    eligible: bool
    reason: str

    ELIGIBLE: ClassVar[str] = "ELIGIBLE"
    STATUS_PARTIAL: ClassVar[str] = "STATUS_PARTIAL"
    STATUS_UNAVAILABLE: ClassVar[str] = "STATUS_UNAVAILABLE"
    STATUS_NOT_MATURE: ClassVar[str] = "STATUS_NOT_MATURE"
    STATUS_NOT_ELIGIBLE: ClassVar[str] = "STATUS_NOT_ELIGIBLE"
    METHODOLOGY_NOT_ALLOWED: ClassVar[str] = "METHODOLOGY_NOT_ALLOWED"

    def __post_init__(self) -> None:
        allowed = {
            self.ELIGIBLE,
            self.STATUS_PARTIAL,
            self.STATUS_UNAVAILABLE,
            self.STATUS_NOT_MATURE,
            self.STATUS_NOT_ELIGIBLE,
            self.METHODOLOGY_NOT_ALLOWED,
        }
        if self.reason not in allowed:
            raise ValueError(
                f"unsupported eligibility reason: {self.reason}"
            )
        if self.eligible != (self.reason == self.ELIGIBLE):
            raise ValueError(
                "eligible must be true exactly when reason is ELIGIBLE"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "reason": self.reason,
        }


class HistoricalOutcomeEligibilityService:
    """
    Classify research eligibility without dropping excluded observations.

    Sprint 16 v1 treats methodology permission first, then observation status.
    COMPLETE is eligible only when the protocol explicitly allows COMPLETE.
    """

    _STATUS_REASON = {
        "PARTIAL": HistoricalOutcomeEligibilityAssessment.STATUS_PARTIAL,
        "UNAVAILABLE": HistoricalOutcomeEligibilityAssessment.STATUS_UNAVAILABLE,
        "NOT_MATURE": HistoricalOutcomeEligibilityAssessment.STATUS_NOT_MATURE,
    }

    def assess(
        self,
        *,
        result: HistoricalMethodologyAwareObservationResult,
        protocol: HistoricalOutcomeResearchProtocol,
    ) -> HistoricalOutcomeEligibilityAssessment:
        if not isinstance(
            result,
            HistoricalMethodologyAwareObservationResult,
        ):
            raise TypeError(
                "result must be a HistoricalMethodologyAwareObservationResult"
            )
        if not isinstance(
            protocol,
            HistoricalOutcomeResearchProtocol,
        ):
            raise TypeError(
                "protocol must be a HistoricalOutcomeResearchProtocol"
            )

        if not protocol.allows_methodology(
            result.methodology.identity_key
        ):
            return HistoricalOutcomeEligibilityAssessment(
                eligible=False,
                reason=(
                    HistoricalOutcomeEligibilityAssessment
                    .METHODOLOGY_NOT_ALLOWED
                ),
            )

        status = result.observation.status
        if status in protocol.eligible_statuses:
            return HistoricalOutcomeEligibilityAssessment(
                eligible=True,
                reason=HistoricalOutcomeEligibilityAssessment.ELIGIBLE,
            )

        return HistoricalOutcomeEligibilityAssessment(
            eligible=False,
            reason=self._STATUS_REASON.get(
                status,
                HistoricalOutcomeEligibilityAssessment.STATUS_NOT_ELIGIBLE,
            ),
        )

    def assess_many(
        self,
        *,
        results: tuple[
            HistoricalMethodologyAwareObservationResult,
            ...,
        ],
        protocol: HistoricalOutcomeResearchProtocol,
    ) -> tuple[
        HistoricalOutcomeEligibilityAssessment,
        ...,
    ]:
        if not isinstance(results, tuple):
            raise TypeError(
                "results must be a tuple"
            )
        return tuple(
            self.assess(
                result=result,
                protocol=protocol,
            )
            for result in results
        )
