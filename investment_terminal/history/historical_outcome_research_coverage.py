"""
Coverage accounting for historical outcome research cohorts.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Any

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_research_eligibility import (
    HistoricalOutcomeEligibilityAssessment,
    HistoricalOutcomeEligibilityService,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeResearchCoverage:
    """Transparent candidate, eligibility, and observation-status accounting."""

    candidate_count: int
    eligible_count: int
    complete_count: int
    partial_count: int
    unavailable_count: int
    not_mature_count: int
    excluded_count: int
    coverage_fraction: float

    def __post_init__(self) -> None:
        integer_fields = {
            "candidate_count": self.candidate_count,
            "eligible_count": self.eligible_count,
            "complete_count": self.complete_count,
            "partial_count": self.partial_count,
            "unavailable_count": self.unavailable_count,
            "not_mature_count": self.not_mature_count,
            "excluded_count": self.excluded_count,
        }
        for field_name, value in integer_fields.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if self.eligible_count > self.candidate_count:
            raise ValueError(
                "eligible_count must not exceed candidate_count"
            )
        if self.excluded_count != (
            self.candidate_count - self.eligible_count
        ):
            raise ValueError(
                "excluded_count must equal candidate_count - eligible_count"
            )

        status_total = (
            self.complete_count
            + self.partial_count
            + self.unavailable_count
            + self.not_mature_count
        )
        if status_total != self.candidate_count:
            raise ValueError(
                "observation status counts must equal candidate_count"
            )

        if (
            isinstance(self.coverage_fraction, bool)
            or not isinstance(self.coverage_fraction, (int, float))
            or not isfinite(float(self.coverage_fraction))
            or not 0.0 <= float(self.coverage_fraction) <= 1.0
        ):
            raise ValueError(
                "coverage_fraction must be a finite number from 0 to 1"
            )

        expected = (
            0.0
            if self.candidate_count == 0
            else self.eligible_count / self.candidate_count
        )
        if abs(
            float(self.coverage_fraction) - expected
        ) > 1e-12:
            raise ValueError(
                "coverage_fraction must equal eligible_count / candidate_count"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_count": self.candidate_count,
            "eligible_count": self.eligible_count,
            "complete_count": self.complete_count,
            "partial_count": self.partial_count,
            "unavailable_count": self.unavailable_count,
            "not_mature_count": self.not_mature_count,
            "excluded_count": self.excluded_count,
            "coverage_fraction": self.coverage_fraction,
        }


class HistoricalOutcomeResearchCoverageService:
    """Summarize research coverage without dropping incomplete observations."""

    _KNOWN_STATUSES = {
        "COMPLETE",
        "PARTIAL",
        "UNAVAILABLE",
        "NOT_MATURE",
    }

    def __init__(
        self,
        *,
        eligibility_service: HistoricalOutcomeEligibilityService | None = None,
    ) -> None:
        self._eligibility_service = (
            eligibility_service
            if eligibility_service is not None
            else HistoricalOutcomeEligibilityService()
        )

    def summarize(
        self,
        *,
        results: tuple[
            HistoricalMethodologyAwareObservationResult,
            ...,
        ],
        protocol: HistoricalOutcomeResearchProtocol,
    ) -> HistoricalOutcomeResearchCoverage:
        if not isinstance(results, tuple):
            raise TypeError(
                "results must be a tuple"
            )
        if not isinstance(
            protocol,
            HistoricalOutcomeResearchProtocol,
        ):
            raise TypeError(
                "protocol must be a HistoricalOutcomeResearchProtocol"
            )

        for result in results:
            if not isinstance(
                result,
                HistoricalMethodologyAwareObservationResult,
            ):
                raise TypeError(
                    "results must contain only "
                    "HistoricalMethodologyAwareObservationResult values"
                )
            if result.observation.status not in self._KNOWN_STATUSES:
                raise ValueError(
                    "unsupported observation status: "
                    f"{result.observation.status}"
                )

        assessments = self._eligibility_service.assess_many(
            results=results,
            protocol=protocol,
        )

        eligible_count = sum(
            1
            for assessment in assessments
            if assessment.eligible
        )
        candidate_count = len(results)

        status_counts = {
            status: 0
            for status in self._KNOWN_STATUSES
        }
        for result in results:
            status_counts[
                result.observation.status
            ] += 1

        return HistoricalOutcomeResearchCoverage(
            candidate_count=candidate_count,
            eligible_count=eligible_count,
            complete_count=status_counts["COMPLETE"],
            partial_count=status_counts["PARTIAL"],
            unavailable_count=status_counts["UNAVAILABLE"],
            not_mature_count=status_counts["NOT_MATURE"],
            excluded_count=(
                candidate_count - eligible_count
            ),
            coverage_fraction=(
                0.0
                if candidate_count == 0
                else eligible_count / candidate_count
            ),
        )
