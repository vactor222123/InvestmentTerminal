"""
Tests for sector-aware fundamental scoring.
"""

from dataclasses import replace
from unittest.mock import Mock

from investment_terminal.market.company_classification_registry import (
    CompanyClassificationRegistry,
)
from investment_terminal.services.sector_aware_fundamental_score_service import (
    SectorAwareFundamentalScoreService,
)
from tests.test_fundamental_score_service import (
    create_snapshot,
)


def create_service() -> SectorAwareFundamentalScoreService:
    return SectorAwareFundamentalScoreService(
        client=Mock(),
        registry=CompanyClassificationRegistry.load(),
    )


def test_payment_network_ignores_generic_liquidity_risks() -> None:
    snapshot = replace(
        create_snapshot(),
        symbol="V",
        current_ratio=0.40,
        quick_ratio=0.20,
    )

    result = create_service().score_snapshot(
        snapshot
    )

    assert (
        "Current ratio is below one."
        not in result.risk_factors
    )
    assert (
        "Quick liquidity is weak."
        not in result.risk_factors
    )
    assert (
        "current_ratio"
        not in result.missing_fields
    )
    assert (
        "quick_ratio"
        not in result.missing_fields
    )


def test_bank_ignores_generic_leverage_and_liquidity_risks() -> None:
    snapshot = replace(
        create_snapshot(),
        symbol="JPM",
        debt_to_equity=8.0,
        current_ratio=0.30,
        quick_ratio=0.10,
    )

    result = create_service().score_snapshot(
        snapshot
    )

    assert (
        "Debt-to-equity is high."
        not in result.risk_factors
    )
    assert (
        "Current ratio is below one."
        not in result.risk_factors
    )
    assert (
        "Quick liquidity is weak."
        not in result.risk_factors
    )


def test_standard_company_keeps_generic_balance_sheet_rules() -> None:
    snapshot = replace(
        create_snapshot(),
        symbol="MSFT",
        current_ratio=0.40,
        quick_ratio=0.20,
    )

    result = create_service().score_snapshot(
        snapshot
    )

    assert (
        "Current ratio is below one."
        in result.risk_factors
    )
    assert (
        "Quick liquidity is weak."
        in result.risk_factors
    )


def test_unclassified_company_falls_back_to_generic_scoring() -> None:
    snapshot = replace(
        create_snapshot(),
        symbol="UNKNOWN",
        current_ratio=0.40,
    )

    result = create_service().score_snapshot(
        snapshot
    )

    assert (
        "Current ratio is below one."
        in result.risk_factors
    )


def test_inapplicable_missing_fields_do_not_reduce_quality() -> None:
    snapshot = replace(
        create_snapshot(),
        symbol="V",
        current_ratio=None,
        quick_ratio=None,
    )

    result = create_service().score_snapshot(
        snapshot
    )

    assert (
        "current_ratio"
        not in result.missing_fields
    )
    assert (
        "quick_ratio"
        not in result.missing_fields
    )