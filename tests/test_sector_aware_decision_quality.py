"""
Tests for sector-aware decision quality labels.
"""

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
from tests.test_fundamental_score_service import (
    create_snapshot,
)


def create_sector_aware_score(
    symbol: str,
    *,
    debt_to_equity: float | None,
    current_ratio: float | None,
    quick_ratio: float | None,
):
    snapshot = replace(
        create_snapshot(),
        symbol=symbol,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        quick_ratio=quick_ratio,
    )
    service = SectorAwareFundamentalScoreService(
        client=Mock(),
        registry=CompanyClassificationRegistry.load(),
    )

    return service.score_snapshot(snapshot)


def test_payment_network_financial_health_uses_normalized_score() -> None:
    score = create_sector_aware_score(
        "V",
        debt_to_equity=0.70,
        current_ratio=0.20,
        quick_ratio=0.10,
    )

    assert DecisionClassifiers._classify_financial_health(
        score
    ) == "ADEQUATE"


def test_bank_without_generic_balance_sheet_metrics_is_unknown() -> None:
    score = create_sector_aware_score(
        "JPM",
        debt_to_equity=8.0,
        current_ratio=0.20,
        quick_ratio=0.10,
    )

    assert DecisionClassifiers._classify_financial_health(
        score
    ) == "UNKNOWN"


def test_standard_company_still_receives_weak_health() -> None:
    score = create_sector_aware_score(
        "MSFT",
        debt_to_equity=3.0,
        current_ratio=0.50,
        quick_ratio=0.40,
    )

    assert DecisionClassifiers._classify_financial_health(
        score
    ) == "WEAK"