"""
Tests for FundamentalScoreService.
"""

import json
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.models.fundamental_snapshot import (
    FundamentalDataQuality,
    FundamentalSnapshot,
)
from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreService,
)


def create_snapshot() -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol="MSFT",
        currency="USD",
        generated_at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
        market_cap=3_450_000_000_000,
        enterprise_value=3_500_000_000_000,
        trailing_pe=25.12,
        forward_pe=19.96,
        peg_ratio=1.21,
        price_to_book=7.80,
        price_to_sales=10.40,
        enterprise_to_ebitda=18.03,
        revenue=331_800_000_000,
        revenue_growth=0.177,
        earnings_growth=0.317,
        eps_trailing=18.50,
        eps_forward=23.28,
        gross_margin=0.6794,
        operating_margin=0.4511,
        net_margin=0.4030,
        return_on_equity=0.3404,
        return_on_assets=0.1409,
        return_on_invested_capital=None,
        total_cash=76_650_000_000,
        total_debt=128_810_000_000,
        debt_to_equity=0.29118,
        current_ratio=1.23,
        quick_ratio=1.098,
        operating_cash_flow=182_930_000_000,
        free_cash_flow=16_360_000_000,
        dividend_yield=0.0081,
        payout_ratio=0.1983,
        data_quality=FundamentalDataQuality(
            available_fields=27,
            total_fields=28,
            completeness_percent=96.43,
            missing_fields=(
                "return_on_invested_capital",
            ),
            source="Yahoo Finance",
            fetched_at=datetime(
                2026,
                8,
                1,
                tzinfo=timezone.utc,
            ),
        ),
    )


def test_score_snapshot_returns_breakdown() -> None:
    service = FundamentalScoreService(
        client=Mock()
    )

    result = service.score_snapshot(
        create_snapshot()
    )

    assert result.symbol == "MSFT"
    assert 0 <= result.raw_score <= 100
    assert 0 <= result.final_score <= 100

    assert result.breakdown.growth > 0
    assert result.breakdown.profitability > 0
    assert result.breakdown.balance_sheet > 0
    assert result.breakdown.cash_flow > 0
    assert result.breakdown.valuation > 0
    assert (
        result.breakdown.shareholder_returns
        > 0
    )

    assert result.data_quality_factor == pytest.approx(
        0.9643
    )
    assert (
        "return_on_invested_capital"
        in result.missing_fields
    )


def test_score_calls_client() -> None:
    snapshot = create_snapshot()

    client = Mock()
    client.get_fundamentals.return_value = snapshot

    result = FundamentalScoreService(
        client=client
    ).score(
        symbol="msft",
        currency="usd",
    )

    assert result.symbol == "MSFT"

    client.get_fundamentals.assert_called_once_with(
        symbol="msft",
        currency="usd",
    )


def test_score_applies_data_quality_factor() -> None:
    snapshot = replace(
        create_snapshot(),
        data_quality=FundamentalDataQuality(
            available_fields=14,
            total_fields=28,
            completeness_percent=50.0,
            missing_fields=(
                "return_on_invested_capital",
            ),
            source="Test",
            fetched_at=datetime.now(
                timezone.utc
            ),
        ),
    )

    result = FundamentalScoreService(
        client=Mock()
    ).score_snapshot(snapshot)

    assert result.final_score == pytest.approx(
        result.raw_score * 0.5,
        abs=0.01,
    )


def test_score_without_quality_returns_zero_final_score() -> None:
    snapshot = replace(
        create_snapshot(),
        data_quality=None,
    )

    result = FundamentalScoreService(
        client=Mock()
    ).score_snapshot(snapshot)

    assert result.raw_score > 0
    assert result.data_quality_factor == 0.0
    assert result.final_score == 0.0
    assert result.classification == "VERY_WEAK"


def test_declining_company_receives_risk_factors() -> None:
    snapshot = replace(
        create_snapshot(),
        revenue_growth=-0.10,
        earnings_growth=-0.20,
        operating_cash_flow=-1.0,
        free_cash_flow=-1.0,
        debt_to_equity=3.0,
        current_ratio=0.7,
        quick_ratio=0.5,
    )

    result = FundamentalScoreService(
        client=Mock()
    ).score_snapshot(snapshot)

    assert result.final_score < 60.0
    assert len(result.risk_factors) > 0


def test_score_result_is_json_serializable() -> None:
    result = FundamentalScoreService(
        client=Mock()
    ).score_snapshot(
        create_snapshot()
    )

    payload = result.to_dict()
    serialized = json.dumps(payload)

    assert '"symbol": "MSFT"' in serialized
    assert isinstance(
        payload["positive_factors"],
        list,
    )
    assert isinstance(
        payload["missing_fields"],
        list,
    )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (85.0, "EXCELLENT"),
        (70.0, "STRONG"),
        (55.0, "FAIR"),
        (40.0, "WEAK"),
        (20.0, "VERY_WEAK"),
    ],
)
def test_classify_score(
    score: float,
    expected: str,
) -> None:
    assert (
        FundamentalScoreService._classify_score(
            score
        )
        == expected
    )


def test_score_rejects_invalid_snapshot() -> None:
    service = FundamentalScoreService(
        client=Mock()
    )

    with pytest.raises(
        TypeError,
        match="FundamentalSnapshot",
    ):
        service.score_snapshot(None)