"""
Additional tests for decision-stage coverage reconstruction.
"""

import pytest

from investment_terminal.market.analysis_coverage_policy import (
    AnalysisCoveragePolicy,
    FULL,
    REDUCED,
    SPECIALIZED_BANK_WARNING,
)


POLICY = AnalysisCoveragePolicy()


def test_risk_factor_assessment_detects_reduced_bank_coverage() -> None:
    assessment = POLICY.assess_risk_factors(
        (
            SPECIALIZED_BANK_WARNING,
        )
    )

    assert assessment.level == REDUCED
    assert assessment.recommendation_cap == "WATCH"
    assert assessment.allocation_eligible is False


def test_risk_factor_assessment_defaults_to_full() -> None:
    assessment = POLICY.assess_risk_factors(
        (
            "Price-to-sales is elevated.",
        )
    )

    assert assessment.level == FULL
    assert assessment.recommendation_cap is None
    assert assessment.allocation_eligible is True


def test_risk_factor_assessment_rejects_list() -> None:
    with pytest.raises(
        TypeError,
        match="tuple",
    ):
        POLICY.assess_risk_factors(
            []
        )