"""
Tests for policy-gap integration into the review package.
"""

import json
from pathlib import Path

from investment_terminal.cli.investment_review_package import (
    main,
)
from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)
from investment_terminal.portfolio.portfolio_policy_gap_service import (
    PortfolioPolicyGapService,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
)
from investment_terminal.review.portfolio_review_adapter import (
    PortfolioReviewAdapter,
)


def create_portfolio() -> CurrentPortfolio:
    return CurrentPortfolio(
        name="Review Gap Test",
        policy=PortfolioPolicy(
            core_target_weight=0.80,
            tactical_target_weight=0.10,
            cash_target_weight=0.10,
            monthly_contribution=2000.0,
            base_currency="EUR",
        ),
        holdings=(
            PortfolioHolding(
                symbol="WORLD",
                name="World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=70.0,
                average_cost=100.0,
                isin="IE00B4L5Y983",
                exchange_ticker="EUNL",
            ),
            PortfolioHolding(
                symbol="MSFT",
                name="Microsoft",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=2.0,
                average_cost=500.0,
                exchange_ticker="MSFT",
            ),
        ),
        cash_balance=2000.0,
    )


def test_adapter_exports_policy_gap() -> None:
    portfolio = create_portfolio()
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )
    gap = PortfolioPolicyGapService().calculate(
        snapshot=snapshot,
        policy=portfolio.policy,
    )

    payload = PortfolioReviewAdapter().adapt(
        snapshot=snapshot,
        market_value=None,
        quotes_source=None,
        policy_gap=gap,
    )

    items = {
        item["key"]: item
        for item in payload["policy_gap"]["items"]
    }

    assert items[
        "CORE_LONG_TERM"
    ]["status"] == "UNDERWEIGHT"
    assert items[
        "CASH_RESERVE"
    ]["status"] == "OVERWEIGHT"


def test_adapter_keeps_policy_gap_optional() -> None:
    portfolio = create_portfolio()
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )

    payload = PortfolioReviewAdapter().adapt(
        snapshot=snapshot,
        market_value=None,
        quotes_source=None,
    )

    assert payload["policy_gap"] is None


def test_cli_exports_policy_gap(
    tmp_path: Path,
) -> None:
    portfolio_path = tmp_path / "portfolio.json"
    output_path = tmp_path / "review.json"

    portfolio_path.write_text(
        json.dumps(
            {
                "name": "CLI Gap Test",
                "policy": {
                    "core_target_weight": 0.80,
                    "tactical_target_weight": 0.10,
                    "cash_target_weight": 0.10,
                    "monthly_contribution": 2000.0,
                    "base_currency": "EUR"
                },
                "cash_balance": 2000.0,
                "holdings": [
                    {
                        "symbol": "WORLD",
                        "name": "World ETF",
                        "asset_type": "ETF",
                        "sleeve": "CORE",
                        "quantity": 70.0,
                        "average_cost": 100.0,
                        "currency": "EUR",
                        "isin": "IE00B4L5Y983",
                        "exchange_ticker": "EUNL"
                    },
                    {
                        "symbol": "MSFT",
                        "name": "Microsoft",
                        "asset_type": "STOCK",
                        "sleeve": "TACTICAL",
                        "quantity": 2.0,
                        "average_cost": 500.0,
                        "currency": "EUR",
                        "isin": None,
                        "exchange_ticker": "MSFT"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    main(
        [
            "--portfolio",
            str(portfolio_path),
            "--portfolio-quotes",
            str(tmp_path / "missing-quotes.json"),
            "--stock-analysis",
            str(tmp_path / "missing-stock.json"),
            "--output",
            str(output_path),
        ]
    )

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8",
        )
    )
    section = payload["sections"]["portfolio"]
    items = {
        item["key"]: item
        for item in section["policy_gap"]["items"]
    }

    assert section["policy_gap"]["total_value"] == 10000.0
    assert items["CORE_LONG_TERM"]["gap_amount"] == 1000.0
    assert items["TACTICAL_TOTAL"]["status"] == "ON_TARGET"
    assert items["CASH_RESERVE"]["gap_amount"] == -1000.0