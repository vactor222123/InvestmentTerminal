"""
Tests for contribution-plan integration into the review package.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.investment_review_package import (
    main,
    resolve_available_capital,
)


def write_portfolio(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "name": "Contribution CLI Test",
                "policy": {
                    "core_target_weight": 0.80,
                    "tactical_target_weight": 0.10,
                    "cash_target_weight": 0.10,
                    "monthly_contribution": 2000.0,
                    "base_currency": "EUR"
                },
                "cash_balance": 2500.0,
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
                        "quantity": 1.0,
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


def test_resolve_available_capital_uses_monthly_default() -> None:
    assert resolve_available_capital(
        explicit_capital=None,
        monthly_contribution=2000.0,
    ) == 2000.0


def test_resolve_available_capital_prefers_explicit_value() -> None:
    assert resolve_available_capital(
        explicit_capital=1600.0,
        monthly_contribution=2000.0,
    ) == 1600.0


def test_resolve_available_capital_rejects_negative_value() -> None:
    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        resolve_available_capital(
            explicit_capital=-1.0,
            monthly_contribution=2000.0,
        )


def test_cli_exports_explicit_contribution_plan(
    tmp_path: Path,
) -> None:
    portfolio_path = tmp_path / "portfolio.json"
    output_path = tmp_path / "review.json"
    write_portfolio(portfolio_path)

    main(
        [
            "--portfolio",
            str(portfolio_path),
            "--available-capital",
            "1600",
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
    plan = payload[
        "sections"
    ][
        "portfolio"
    ][
        "contribution_plan"
    ]

    assert plan["available_capital"] == 1600.0
    assert plan["deployable_capital"] == 1500.0
    assert plan["retained_cash"] == 100.0
    assert [
        item["key"]
        for item in plan["items"]
    ] == [
        "CORE_LONG_TERM",
        "TACTICAL_TOTAL",
    ]


def test_cli_uses_monthly_contribution_by_default(
    tmp_path: Path,
) -> None:
    portfolio_path = tmp_path / "portfolio.json"
    output_path = tmp_path / "review.json"
    write_portfolio(portfolio_path)

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
    plan = payload[
        "sections"
    ][
        "portfolio"
    ][
        "contribution_plan"
    ]

    assert plan["available_capital"] == 2000.0
    assert plan["deployable_capital"] == 1500.0
    assert plan["retained_cash"] == 500.0