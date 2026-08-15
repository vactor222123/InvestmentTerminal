"""
Regression tests for explicit portfolio files and incomplete quote coverage.
"""

import json
from pathlib import Path

from investment_terminal.cli.investment_review_package import (
    main,
)


EXAMPLE_PORTFOLIO = Path(
    "data/portfolios/current_portfolio.example.json"
)


def test_review_package_uses_tracked_portfolio_fixture(
    tmp_path: Path,
) -> None:
    output = tmp_path / "review.json"

    main(
        [
            "--portfolio",
            str(EXAMPLE_PORTFOLIO),
            "--output",
            str(output),
        ]
    )

    payload = json.loads(
        output.read_text(
            encoding="utf-8",
        )
    )

    assert (
        payload["sections"]["portfolio"]
        ["cost_basis_snapshot"]
        ["portfolio_name"]
        == "Example Investment Portfolio"
    )


def test_incomplete_quotes_fall_back_to_cost_basis(
    tmp_path: Path,
) -> None:
    portfolio_path = tmp_path / "portfolio.json"
    quotes_path = tmp_path / "quotes.json"
    output_path = tmp_path / "review.json"

    portfolio_path.write_text(
        json.dumps(
            {
                "name": "Test",
                "policy": {
                    "core_target_weight": 0.85,
                    "tactical_target_weight": 0.10,
                    "cash_target_weight": 0.05,
                    "monthly_contribution": 2000.0,
                    "base_currency": "EUR"
                },
                "cash_balance": 1000.0,
                "holdings": [
                    {
                        "symbol": "WORLD",
                        "name": "World ETF",
                        "asset_type": "ETF",
                        "sleeve": "CORE",
                        "quantity": 10.0,
                        "average_cost": 100.0,
                        "currency": "EUR",
                        "isin": "IE00B4L5Y983",
                        "exchange_ticker": "EUNL"
                    },
                    {
                        "symbol": "EMIMI",
                        "name": "EM IMI ETF",
                        "asset_type": "ETF",
                        "sleeve": "CORE",
                        "quantity": 10.0,
                        "average_cost": 40.0,
                        "currency": "EUR",
                        "isin": "IE00BKM4GZ66",
                        "exchange_ticker": "IS3N"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    quotes_path.write_text(
        json.dumps(
            {
                "quotes": [
                    {
                        "instrument_key": "IE00B4L5Y983",
                        "exchange_ticker": "EUNL",
                        "price": 110.0,
                        "currency": "EUR",
                        "quoted_at": "2026-08-01T18:00:00+00:00",
                        "source": "TEST"
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
            str(quotes_path),
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

    assert (
        payload["sections"]["portfolio"]["status"]
        == "COST_BASIS_ONLY"
    )
    assert (
        payload["sections"]["portfolio"]["market_value"]
        is None
    )
