"""
Explicit sample-sufficiency policy for historical outcome research.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.history.historical_outcome_research_coverage import (
    HistoricalOutcomeResearchCoverage,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeSampleAssessment:
    """Machine-readable assessment of whether a research sample is large enough."""

    status: str
    eligible_sample_size: int
    minimum_required_sample_size: int
    shortfall: int

    INSUFFICIENT: ClassVar[str] = "INSUFFICIENT"
    SUFFICIENT: ClassVar[str] = "SUFFICIENT"

    def __post_init__(self) -> None:
        if self.status not in {
            self.INSUFFICIENT,
            self.SUFFICIENT,
        }:
            raise ValueError(
                f"unsupported sample sufficiency status: {self.status}"
            )

        for field_name, value in {
            "eligible_sample_size": self.eligible_sample_size,
            "minimum_required_sample_size": self.minimum_required_sample_size,
            "shortfall": self.shortfall,
        }.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if self.minimum_required_sample_size <= 0:
            raise ValueError(
                "minimum_required_sample_size must be greater than zero"
            )

        expected_shortfall = max(
            0,
            self.minimum_required_sample_size
            - self.eligible_sample_size,
        )
        if self.shortfall != expected_shortfall:
            raise ValueError(
                "shortfall must equal the remaining samples required"
            )

        expected_status = (
            self.SUFFICIENT
            if self.eligible_sample_size
            >= self.minimum_required_sample_size
            else self.INSUFFICIENT
        )
        if self.status != expected_status:
            raise ValueError(
                "status does not match sample-size threshold"
            )

    @property
    def sufficient(self) -> bool:
        return self.status == self.SUFFICIENT

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "sufficient": self.sufficient,
            "eligible_sample_size": self.eligible_sample_size,
            "minimum_required_sample_size": (
                self.minimum_required_sample_size
            ),
            "shortfall": self.shortfall,
        }


class HistoricalOutcomeSampleSufficiencyService:
    """
    Compare eligible research evidence with the protocol-selected threshold.

    The service does not choose a universal statistical threshold. The minimum
    sample size is an explicit, versioned research-protocol parameter.
    """

    def assess(
        self,
        *,
        coverage: HistoricalOutcomeResearchCoverage,
        protocol: HistoricalOutcomeResearchProtocol,
    ) -> HistoricalOutcomeSampleAssessment:
        if not isinstance(
            coverage,
            HistoricalOutcomeResearchCoverage,
        ):
            raise TypeError(
                "coverage must be a HistoricalOutcomeResearchCoverage"
            )
        if not isinstance(
            protocol,
            HistoricalOutcomeResearchProtocol,
        ):
            raise TypeError(
                "protocol must be a HistoricalOutcomeResearchProtocol"
            )

        eligible_sample_size = coverage.eligible_count
        minimum = protocol.minimum_complete_sample_size
        shortfall = max(
            0,
            minimum - eligible_sample_size,
        )

        return HistoricalOutcomeSampleAssessment(
            status=(
                HistoricalOutcomeSampleAssessment.SUFFICIENT
                if eligible_sample_size >= minimum
                else HistoricalOutcomeSampleAssessment.INSUFFICIENT
            ),
            eligible_sample_size=eligible_sample_size,
            minimum_required_sample_size=minimum,
            shortfall=shortfall,
        )
