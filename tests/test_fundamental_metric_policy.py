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
        classification(
            business_model
        ),
        metric,
    )

    assert result.applicable is False
    assert business_model in result.reason


def test_standard_company_keeps_liquidity_metrics() -> None:
    result = POLICY.evaluate(
        classification(
            "STANDARD"
        ),
        "current_ratio",
    )

    assert result.applicable is True


def test_bank_excludes_debt_to_equity() -> None:
    result = POLICY.evaluate(
        classification(
            "BANK"
        ),
        "debt_to_equity",
    )

    assert result.applicable is False
    assert "structural" in result.reason


def test_payment_network_keeps_debt_to_equity() -> None:
    result = POLICY.evaluate(
        classification(
            "PAYMENT_NETWORK"
        ),
        "debt_to_equity",
    )

    assert result.applicable is True


def test_growth_metric_remains_applicable_to_bank() -> None:
    result = POLICY.evaluate(
        classification(
            "BANK"
        ),
        "earnings_growth",
    )

    assert result.applicable is True


def test_unknown_metric_is_not_applicable() -> None:
    result = POLICY.evaluate(
        classification(
            "STANDARD"
        ),
        "mystery_metric",
    )

    assert result.applicable is False
    assert "not registered" in result.reason


def test_metric_name_is_normalized() -> None:
    result = POLICY.evaluate(
        classification(
            "STANDARD"
        ),
        " Current Ratio ",
    )

    assert result.metric_name == (
        "current_ratio"
    )


def test_excluded_metrics_for_bank() -> None:
    excluded = POLICY.excluded_metrics(
        classification(
            "BANK"
        )
    )

    assert {
        result.metric_name
        for result in excluded
    } == {
        "current_ratio",
        "quick_ratio",
        "debt_to_equity",
    }


def test_applicable_metrics_for_payment_network() -> None:
    metrics = POLICY.applicable_metrics(
        classification(
            "PAYMENT_NETWORK"
        )
    )

    assert "current_ratio" not in metrics
    assert "quick_ratio" not in metrics
    assert "debt_to_equity" in metrics
    assert "free_cash_flow" in metrics


def test_rejects_invalid_classification() -> None:
    with pytest.raises(
        TypeError,
        match="CompanyClassification",
    ):
        POLICY.evaluate(
            None,
            "current_ratio",
        )