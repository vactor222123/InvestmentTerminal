"""Tests for analysis-coverage safety policy."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from investment_terminal.market.analysis_coverage_policy import (
    AnalysisCoveragePolicy,
    FULL,
    INSUFFICIENT,
    REDUCED,
    SPECIALIZED_BANK_WARNING,
)
from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreBreakdown,
    FundamentalScoreService,
)
from tests.test_fundamental_score_service import (
    create_snapshot,
)


POLICY = AnalysisCoveragePolicy()


def create_full_result():
    return FundamentalScoreService(
        Mock()
    ).score_snapshot(
        create_snapshot()
    )


def create_reduced_bank_result():
    result = create_full_result()
    breakdown = replace(
        result.breakdown,
        balance_sheet_max=0.0,
        cash_flow_max=0.0,
        valuation_max=15.0,
    )

    return replace(
        result,
        breakdown=breakdown,
        data_quality_factor=0.9167,
        risk_factors=(
            *result.risk_factors,
            SPECIALIZED_BANK_WARNING,
        ),
    )


def test_full_coverage_allows_recommendation_and_allocation() -> None:
    assessment = POLICY.assess(
        create_full_result()
    )

    assert assessment.level == FULL
    assert assessment.recommendation_cap is None
    assert assessment.allocation_eligible is True
    assert assessment.reasons == ()


def test_reduced_bank_coverage_caps_at_watch() -> None:
    assessment = POLICY.assess(
        create_reduced_bank_result()
    )

    assert assessment.level == REDUCED
    assert assessment.recommendation_cap == "WATCH"
    assert assessment.allocation_eligible is False
    assert any(
        "bank metrics"
        in reason.lower()
        for reason in assessment.reasons
    )


def test_low_data_quality_is_insufficient() -> None:
    result = replace(
        create_full_result(),
        data_quality_factor=0.70,
    )

    assessment = POLICY.assess(result)

    assert assessment.level == INSUFFICIENT
    assert assessment.recommendation_cap == "AVOID"
    assert assessment.allocation_eligible is False


def test_too_small_active_framework_is_insufficient() -> None:
    result = create_full_result()
    result = replace(
        result,
        breakdown=FundamentalScoreBreakdown(
            growth=10.0,
            profitability=10.0,
            balance_sheet=0.0,
            cash_flow=0.0,
            valuation=0.0,
            shareholder_returns=0.0,
            growth_max=20.0,
            profitability_max=25.0,
            balance_sheet_max=0.0,
            cash_flow_max=0.0,
            valuation_max=0.0,
            shareholder_returns_max=0.0,
        ),
    )

    assessment = POLICY.assess(result)

    assert assessment.level == INSUFFICIENT
    assert assessment.recommendation_cap == "AVOID"


def test_assessment_is_json_ready() -> None:
    payload = POLICY.assess(
        create_reduced_bank_result()
    ).to_dict()

    assert payload["level"] == REDUCED
    assert payload["recommendation_cap"] == "WATCH"
    assert payload["allocation_eligible"] is False
    assert isinstance(payload["reasons"], list)


def test_policy_rejects_invalid_score() -> None:
    with pytest.raises(
        TypeError,
        match="FundamentalScoreResult",
    ):
        POLICY.assess(None)