"""Tests for business-model-aware metric applicability."""

from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)
from investment_terminal.market.fundamental_metric_policy import (
    FundamentalMetricPolicy,
)


POLICY = FundamentalMetricPolicy()
BANK = CompanyClassification(
    symbol="TEST",
    sector="Financial Services",
    industry="Banks Diversified",
    business_model="BANK",
)


def test_bank_excludes_generic_cash_flow_metrics() -> None:
    assert POLICY.is_applicable(
        BANK,
        "operating_cash_flow",
    ) is False
    assert POLICY.is_applicable(
        BANK,
        "free_cash_flow",
    ) is False


def test_bank_excludes_enterprise_to_ebitda() -> None:
    assert POLICY.is_applicable(
        BANK,
        "enterprise_to_ebitda",
    ) is False


def test_bank_keeps_remaining_generic_valuation_metrics() -> None:
    assert POLICY.is_applicable(BANK, "forward_pe") is True
    assert POLICY.is_applicable(BANK, "peg_ratio") is True
    assert POLICY.is_applicable(BANK, "price_to_sales") is True


def test_bank_excluded_metric_set_is_complete() -> None:
    excluded = {
        item.metric_name
        for item in POLICY.excluded_metrics(BANK)
    }

    assert excluded == {
        "current_ratio",
        "quick_ratio",
        "debt_to_equity",
        "operating_cash_flow",
        "free_cash_flow",
        "enterprise_to_ebitda",
    }