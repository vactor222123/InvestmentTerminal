"""
Tests for business-model-aware metric applicability.
"""

import pytest

from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)
from investment_terminal.market.fundamental_metric_policy import (
    FundamentalMetricPolicy,
)


POLICY = FundamentalMetricPolicy()


def classification(
    business_model: str,
) -> CompanyClassification:
    return CompanyClassification(
        symbol="TEST",
        sector="Test Sector",
        industry="Test Industry",
        business_model=business_model,
    )


@pytest.mark.parametrize(
    "metric",
    [
        "current_ratio",
        "quick_ratio",
    ],
)
@pytest.mark.parametrize(
    "business_model",
    [
        "BANK",
        "PAYMENT_NETWORK",
        "INSURER",
    ],
)
def test_special_models_exclude_generic_liquidity(
    business_model: str,
    metric: str,
) -> None:
    result = POLICY.evaluate(
        classification(business_model),
        metric,
    )

    assert result.applicable is False
    assert business_model in result.reason


def test_standard_company_keeps_liquidity_metrics() -> None:
    assert POLICY.is_applicable(
        classification("STANDARD"),
        "current_ratio",
    ) is True


def test_bank_excludes_debt_to_equity() -> None:
    result = POLICY.evaluate(
        classification("BANK"),
        "debt_to_equity",
    )

    assert result.applicable is False
    assert "structural" in result.reason


def test_policy_uses_snapshot_field_names() -> None:
    metrics = POLICY.applicable_metrics(
        classification("STANDARD")
    )

    assert "forward_pe" in metrics
    assert "enterprise_to_ebitda" in metrics
    assert "payout_ratio" in metrics


def test_unknown_metric_is_not_applicable() -> None:
    result = POLICY.evaluate(
        classification("STANDARD"),
        "mystery_metric",
    )

    assert result.applicable is False
    assert "not registered" in result.reason