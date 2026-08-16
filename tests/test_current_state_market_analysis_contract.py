from datetime import datetime, timezone

import pytest

from investment_terminal.analysis.current_state_market_analysis import (
    CURRENT_STATE_EQUITY_ANALYSIS_IDENTITY,
    CurrentStateEquityAnalysisResult,
    require_current_state_equity_analysis_result,
)
from investment_terminal.exporters.portfolio_exporter import (
    PortfolioExportPackage,
)


def test_canonical_current_state_identity_is_versioned() -> None:
    assert CURRENT_STATE_EQUITY_ANALYSIS_IDENTITY == (
        "CURRENT_STATE_EQUITY_ANALYSIS@1"
    )


def test_canonical_result_reuses_existing_typed_export_package() -> None:
    assert CurrentStateEquityAnalysisResult is PortfolioExportPackage


def test_contract_rejects_untyped_payloads() -> None:
    with pytest.raises(
        TypeError,
        match="PortfolioExportPackage",
    ):
        require_current_state_equity_analysis_result(
            {
                "schema_version": "1.3",
            }
        )


def test_contract_does_not_create_a_second_serialization_schema() -> None:
    assert not hasattr(
        CurrentStateEquityAnalysisResult,
        "CURRENT_STATE_EQUITY_ANALYSIS_IDENTITY",
    )


def test_canonical_result_contract_is_not_a_review_package_contract() -> None:
    from investment_terminal.analysis import current_state_market_analysis

    namespace = vars(
        current_state_market_analysis
    )

    assert "InvestmentReviewPackage" not in namespace
    assert "InvestmentReviewPackageBuilder" not in namespace
    assert "PortfolioAnalysisReviewAdapter" not in namespace
