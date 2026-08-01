"""Tests for bank-aware fundamental scoring."""

from dataclasses import replace
from unittest.mock import Mock

from investment_terminal.decision_engine.classifiers import (
    DecisionClassifiers,
)
from investment_terminal.market.company_classification_registry import (
    CompanyClassificationRegistry,
)
from investment_terminal.services.sector_aware_fundamental_score_service import (
    SectorAwareFundamentalScoreService,
)
from tests.test_fundamental_score_service import create_snapshot


def create_service() -> SectorAwareFundamentalScoreService:
    return SectorAwareFundamentalScoreService(
        client=Mock(),
        registry=CompanyClassificationRegistry.load(),
    )


def create_bank_snapshot():
    return replace(
        create_snapshot(),
        symbol="JPM",
        debt_to_equity=8.0,
        current_ratio=None,
        quick_ratio=None,
        operating_cash_flow=None,
        free_cash_flow=None,
        enterprise_to_ebitda=None,
    )


def test_bank_excluded_fields_are_not_missing() -> None:
    result = create_service().score_snapshot(
        create_bank_snapshot()
    )

    assert "debt_to_equity" not in result.missing_fields
    assert "current_ratio" not in result.missing_fields
    assert "quick_ratio" not in result.missing_fields
    assert "operating_cash_flow" not in result.missing_fields
    assert "free_cash_flow" not in result.missing_fields
    assert "enterprise_to_ebitda" not in result.missing_fields


def test_bank_components_use_reduced_maxima() -> None:
    result = create_service().score_snapshot(
        create_bank_snapshot()
    )

    assert result.breakdown.balance_sheet_max == 0.0
    assert result.breakdown.cash_flow_max == 0.0
    assert result.breakdown.valuation_max == 15.0


def test_bank_has_no_generic_cash_flow_risks() -> None:
    result = create_service().score_snapshot(
        create_bank_snapshot()
    )

    assert (
        "Operating cash flow is negative."
        not in result.risk_factors
    )
    assert (
        "Free cash flow is negative."
        not in result.risk_factors
    )


def test_bank_financial_health_is_unknown() -> None:
    result = create_service().score_snapshot(
        create_bank_snapshot()
    )

    assert DecisionClassifiers._classify_financial_health(
        result
    ) == "UNKNOWN"


def test_bank_business_quality_uses_profitability_only() -> None:
    result = create_service().score_snapshot(
        create_bank_snapshot()
    )

    assert result.breakdown.cash_flow_max == 0.0
    assert DecisionClassifiers._classify_business_quality(
        result
    ) != "UNKNOWN"


def test_bank_score_contains_coverage_warning() -> None:
    result = create_service().score_snapshot(
        create_bank_snapshot()
    )

    assert any(
        "Specialized bank metrics"
        in factor
        for factor in result.risk_factors
    )