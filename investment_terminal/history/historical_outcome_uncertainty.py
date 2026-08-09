"""
Transparent uncertainty reporting for historical outcome research.
"""

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Any, ClassVar

from investment_terminal.history.historical_outcome_descriptive_summary import (
    HistoricalOutcomeDescriptiveSummary,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeUncertaintySummary:
    """
    Explicit uncertainty metadata for a descriptive historical sample.

    This model reports sample dispersion and uncertainty of the historical
    sample mean. It is not predictive confidence and does not estimate the
    probability that a recommendation is correct or successful.
    """

    method: str
    sample_size: int
    sample_standard_deviation: float | None
    standard_error_of_mean: float | None
    confidence_interval_method: str | None
    confidence_level: float | None
    confidence_interval_lower: float | None
    confidence_interval_upper: float | None
    warning: str | None

    SAMPLE_STANDARD_ERROR: ClassVar[str] = "SAMPLE_STANDARD_ERROR"

    def __post_init__(self) -> None:
        if self.method != self.SAMPLE_STANDARD_ERROR:
            raise ValueError(
                f"unsupported uncertainty method: {self.method}"
            )

        if (
            isinstance(self.sample_size, bool)
            or not isinstance(self.sample_size, int)
            or self.sample_size <= 0
        ):
            raise ValueError(
                "sample_size must be a positive integer"
            )

        for field_name in (
            "sample_standard_deviation",
            "standard_error_of_mean",
            "confidence_level",
            "confidence_interval_lower",
            "confidence_interval_upper",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(float(value))
            ):
                raise ValueError(
                    f"{field_name} must be a finite number or None"
                )

        if (
            self.sample_standard_deviation is not None
            and self.sample_standard_deviation < 0.0
        ):
            raise ValueError(
                "sample_standard_deviation must be non-negative"
            )
        if (
            self.standard_error_of_mean is not None
            and self.standard_error_of_mean < 0.0
        ):
            raise ValueError(
                "standard_error_of_mean must be non-negative"
            )

        if self.sample_size == 1:
            if self.sample_standard_deviation is not None:
                raise ValueError(
                    "sample_standard_deviation must be None for one observation"
                )
            if self.standard_error_of_mean is not None:
                raise ValueError(
                    "standard_error_of_mean must be None for one observation"
                )
        else:
            if self.sample_standard_deviation is None:
                raise ValueError(
                    "sample_standard_deviation is required for multiple observations"
                )
            if self.standard_error_of_mean is None:
                raise ValueError(
                    "standard_error_of_mean is required for multiple observations"
                )

        interval_values = (
            self.confidence_interval_method,
            self.confidence_level,
            self.confidence_interval_lower,
            self.confidence_interval_upper,
        )
        if any(
            value is not None
            for value in interval_values
        ):
            raise ValueError(
                "confidence interval fields must remain None unless "
                "an explicit interval policy is implemented"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "sample_size": self.sample_size,
            "sample_standard_deviation": self.sample_standard_deviation,
            "standard_error_of_mean": self.standard_error_of_mean,
            "confidence_interval_method": self.confidence_interval_method,
            "confidence_level": self.confidence_level,
            "confidence_interval_lower": self.confidence_interval_lower,
            "confidence_interval_upper": self.confidence_interval_upper,
            "warning": self.warning,
        }


class HistoricalOutcomeUncertaintyService:
    """
    Produce protocol-aware uncertainty from a descriptive sample summary.

    Sprint 16 v1 supports SAMPLE_STANDARD_ERROR only. Confidence intervals are
    intentionally withheld because the current protocol model does not yet
    specify an interval method or confidence level.
    """

    INTERVAL_WARNING = (
        "Confidence interval not reported: the research protocol does not "
        "specify an explicit interval method and confidence level"
    )
    SINGLE_OBSERVATION_WARNING = (
        "Uncertainty cannot be estimated from one observation"
    )

    def summarize(
        self,
        *,
        descriptive_summary: HistoricalOutcomeDescriptiveSummary,
        protocol: HistoricalOutcomeResearchProtocol,
    ) -> HistoricalOutcomeUncertaintySummary:
        if not isinstance(
            descriptive_summary,
            HistoricalOutcomeDescriptiveSummary,
        ):
            raise TypeError(
                "descriptive_summary must be a "
                "HistoricalOutcomeDescriptiveSummary"
            )
        if not isinstance(
            protocol,
            HistoricalOutcomeResearchProtocol,
        ):
            raise TypeError(
                "protocol must be a HistoricalOutcomeResearchProtocol"
            )

        if (
            protocol.uncertainty_policy
            != HistoricalOutcomeResearchProtocol.SAMPLE_STANDARD_ERROR
        ):
            raise ValueError(
                "unsupported research uncertainty policy: "
                f"{protocol.uncertainty_policy}"
            )

        sample_size = descriptive_summary.count
        sample_sd = descriptive_summary.sample_standard_deviation

        if sample_size == 1:
            return HistoricalOutcomeUncertaintySummary(
                method=HistoricalOutcomeUncertaintySummary.SAMPLE_STANDARD_ERROR,
                sample_size=1,
                sample_standard_deviation=None,
                standard_error_of_mean=None,
                confidence_interval_method=None,
                confidence_level=None,
                confidence_interval_lower=None,
                confidence_interval_upper=None,
                warning=self.SINGLE_OBSERVATION_WARNING,
            )

        assert sample_sd is not None
        standard_error = sample_sd / sqrt(sample_size)

        return HistoricalOutcomeUncertaintySummary(
            method=HistoricalOutcomeUncertaintySummary.SAMPLE_STANDARD_ERROR,
            sample_size=sample_size,
            sample_standard_deviation=sample_sd,
            standard_error_of_mean=standard_error,
            confidence_interval_method=None,
            confidence_level=None,
            confidence_interval_lower=None,
            confidence_interval_upper=None,
            warning=self.INTERVAL_WARNING,
        )
