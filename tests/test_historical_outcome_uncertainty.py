"""
Tests for transparent historical outcome uncertainty reporting.
"""

from math import sqrt

import pytest

from investment_terminal.history.historical_outcome_descriptive_summary import (
    HistoricalOutcomeDescriptiveSummary,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_uncertainty import (
    HistoricalOutcomeUncertaintyService,
    HistoricalOutcomeUncertaintySummary,
)


def protocol(
    *,
    uncertainty_policy: str = "SAMPLE_STANDARD_ERROR",
) -> HistoricalOutcomeResearchProtocol:
    return HistoricalOutcomeResearchProtocol(
        protocol_id="DESCRIPTIVE_OUTCOME_RESEARCH",
        version=1,
        allowed_methodology_identities=(
            "ELAPSED_DAYS_EXACT_CLOSE@1",
        ),
        eligible_statuses=(
            "COMPLETE",
        ),
        minimum_complete_sample_size=5,
        grouping_dimensions=(
            "METHODOLOGY_IDENTITY",
            "WINDOW_KIND",
            "WINDOW_VALUE",
        ),
        missing_evidence_policy="KEEP_VISIBLE",
        uncertainty_policy=uncertainty_policy,
        claim_policy="DESCRIPTIVE_ONLY",
    )


def summary(
    *,
    count: int,
    sample_sd: float | None,
) -> HistoricalOutcomeDescriptiveSummary:
    return HistoricalOutcomeDescriptiveSummary(
        count=count,
        mean_price_change_fraction=0.02,
        median_price_change_fraction=0.02,
        minimum_price_change_fraction=0.01,
        maximum_price_change_fraction=0.03,
        sample_standard_deviation=sample_sd,
        positive_movement_count=count,
        negative_movement_count=0,
        zero_movement_count=0,
    )


def test_multiple_observations_report_standard_error() -> None:
    result = HistoricalOutcomeUncertaintyService().summarize(
        descriptive_summary=summary(
            count=4,
            sample_sd=0.10,
        ),
        protocol=protocol(),
    )

    assert result.method == "SAMPLE_STANDARD_ERROR"
    assert result.sample_size == 4
    assert result.sample_standard_deviation == pytest.approx(0.10)
    assert result.standard_error_of_mean == pytest.approx(
        0.10 / sqrt(4)
    )


def test_confidence_interval_is_not_invented() -> None:
    result = HistoricalOutcomeUncertaintyService().summarize(
        descriptive_summary=summary(
            count=9,
            sample_sd=0.06,
        ),
        protocol=protocol(),
    )

    assert result.confidence_interval_method is None
    assert result.confidence_level is None
    assert result.confidence_interval_lower is None
    assert result.confidence_interval_upper is None
    assert "does not specify" in (
        result.warning or ""
    )


def test_single_observation_has_explicit_uncertainty_warning() -> None:
    result = HistoricalOutcomeUncertaintyService().summarize(
        descriptive_summary=HistoricalOutcomeDescriptiveSummary(
            count=1,
            mean_price_change_fraction=0.02,
            median_price_change_fraction=0.02,
            minimum_price_change_fraction=0.02,
            maximum_price_change_fraction=0.02,
            sample_standard_deviation=None,
            positive_movement_count=1,
            negative_movement_count=0,
            zero_movement_count=0,
        ),
        protocol=protocol(),
    )

    assert result.sample_standard_deviation is None
    assert result.standard_error_of_mean is None
    assert result.warning == (
        "Uncertainty cannot be estimated from one observation"
    )


def test_zero_variance_has_zero_standard_error() -> None:
    result = HistoricalOutcomeUncertaintyService().summarize(
        descriptive_summary=summary(
            count=5,
            sample_sd=0.0,
        ),
        protocol=protocol(),
    )

    assert result.standard_error_of_mean == 0.0


def test_serialization_is_explicit_and_non_predictive() -> None:
    result = HistoricalOutcomeUncertaintyService().summarize(
        descriptive_summary=summary(
            count=4,
            sample_sd=0.08,
        ),
        protocol=protocol(),
    )

    data = result.to_dict()

    assert data["method"] == "SAMPLE_STANDARD_ERROR"
    assert data["sample_size"] == 4
    assert data["confidence_level"] is None
    assert "predictive_confidence" not in data
    assert "success_probability" not in data


def test_unsupported_protocol_policy_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported research uncertainty policy",
    ):
        HistoricalOutcomeUncertaintyService().summarize(
            descriptive_summary=summary(
                count=4,
                sample_sd=0.08,
            ),
            protocol=protocol(
                uncertainty_policy="BOOTSTRAP_CONFIDENCE_INTERVAL",
            ),
        )


def test_model_rejects_implicit_confidence_interval() -> None:
    with pytest.raises(
        ValueError,
        match="confidence interval fields",
    ):
        HistoricalOutcomeUncertaintySummary(
            method="SAMPLE_STANDARD_ERROR",
            sample_size=4,
            sample_standard_deviation=0.10,
            standard_error_of_mean=0.05,
            confidence_interval_method="NORMAL_APPROXIMATION",
            confidence_level=0.95,
            confidence_interval_lower=-0.08,
            confidence_interval_upper=0.12,
            warning=None,
        )


def test_service_rejects_invalid_inputs() -> None:
    service = HistoricalOutcomeUncertaintyService()

    with pytest.raises(
        TypeError,
        match="descriptive_summary",
    ):
        service.summarize(
            descriptive_summary=object(),  # type: ignore[arg-type]
            protocol=protocol(),
        )

    with pytest.raises(
        TypeError,
        match="protocol",
    ):
        service.summarize(
            descriptive_summary=summary(
                count=4,
                sample_sd=0.08,
            ),
            protocol=object(),  # type: ignore[arg-type]
        )
