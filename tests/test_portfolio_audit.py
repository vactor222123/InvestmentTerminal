"""
Tests for portfolio configuration auditing.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.portfolio_audit import (
    main,
)
from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)
from investment_terminal.portfolio.portfolio_audit_service import (
    PortfolioConfigurationAuditService,
)


def create_policy() -> PortfolioPolicy:
    return PortfolioPolicy(
        core_target_weight=0.85,
        tactical_target_weight=0.10,
        cash_target_weight=0.05,
        monthly_contribution=2000.0,
        base_currency="EUR",
    )


def test_empty_portfolio_is_valid_but_not_ready() -> None:
    result = (
        PortfolioConfigurationAuditService()
        .audit(
            CurrentPortfolio(
                name="Empty",
                policy=create_policy(),
                holdings=(),
                cash_balance=1600.0,
            )
        )
    )

    assert result.is_valid is True
    assert result.is_market_data_ready is False
    assert result.warning_count == 1
    assert result.issues[0].code == (
        "EMPTY_PORTFOLIO"
    )


def test_holding_with_ticker_is_market_data_ready() -> None:
    portfolio = CurrentPortfolio(
        name="Ready",
        policy=create_policy(),
        holdings=(
            PortfolioHolding(
                symbol="WORLD",
                name="World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=10.0,
                average_cost=100.0,
                isin="IE00B4L5Y983",
                exchange_ticker="IWDA",
            ),
        ),
        cash_balance=1600.0,
    )

    result = (
        PortfolioConfigurationAuditService()
        .audit(
            portfolio
        )
    )

    assert result.market_data_ready_count == 1
    assert result.is_market_data_ready is True


def test_missing_ticker_creates_warning() -> None:
    portfolio = CurrentPortfolio(
        name="Missing ticker",
        policy=create_policy(),
        holdings=(
            PortfolioHolding(
                symbol="WORLD",
                name="World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=10.0,
                average_cost=100.0,
                isin="IE00B4L5Y983",
            ),
        ),
        cash_balance=1600.0,
    )

    result = (
        PortfolioConfigurationAuditService()
        .audit(
            portfolio
        )
    )

    assert result.is_market_data_ready is False
    assert result.warning_count == 1
    assert result.issues[0].code == (
        "MISSING_MARKET_TICKER"
    )


def test_foreign_currency_creates_fx_information() -> None:
    portfolio = CurrentPortfolio(
        name="USD stock",
        policy=create_policy(),
        holdings=(
            PortfolioHolding(
                symbol="MSFT",
                name="Microsoft",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=1.0,
                average_cost=400.0,
                currency="USD",
                exchange_ticker="MSFT",
            ),
        ),
        cash_balance=1600.0,
    )

    result = (
        PortfolioConfigurationAuditService()
        .audit(
            portfolio
        )
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert "FX_CONVERSION_REQUIRED" in codes
    assert "STOCK_ISIN_OPTIONAL" in codes
    assert result.is_market_data_ready is True


def test_audit_rejects_invalid_portfolio() -> None:
    with pytest.raises(
        TypeError,
        match="CurrentPortfolio",
    ):
        PortfolioConfigurationAuditService().audit(
            None
        )


def write_empty_portfolio(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "name": "Empty Test Portfolio",
                "policy": {
                    "core_target_weight": 0.85,
                    "tactical_target_weight": 0.10,
                    "cash_target_weight": 0.05,
                    "monthly_contribution": 2000.0,
                    "base_currency": "EUR"
                },
                "cash_balance": 1600.0,
                "holdings": []
            }
        ),
        encoding="utf-8",
    )


def test_cli_prints_empty_portfolio_audit(
    tmp_path: Path,
    capsys,
) -> None:
    portfolio_path = (
        tmp_path
        / "empty_portfolio.json"
    )
    write_empty_portfolio(
        portfolio_path
    )

    main(
        [
            "--portfolio",
            str(portfolio_path),
        ]
    )

    output = capsys.readouterr().out

    assert (
        "Current Portfolio Configuration Audit"
        in output
    )
    assert "Empty Test Portfolio" in output
    assert "EMPTY_PORTFOLIO" in output


def test_cli_prints_json_for_empty_portfolio(
    tmp_path: Path,
    capsys,
) -> None:
    portfolio_path = (
        tmp_path
        / "empty_portfolio.json"
    )
    write_empty_portfolio(
        portfolio_path
    )

    main(
        [
            "--portfolio",
            str(portfolio_path),
            "--json",
        ]
    )

    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload["holding_count"] == 0
    assert payload["is_market_data_ready"] is False


def test_cli_strict_fails_for_empty_portfolio(
    tmp_path: Path,
) -> None:
    portfolio_path = (
        tmp_path
        / "empty_portfolio.json"
    )
    write_empty_portfolio(
        portfolio_path
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--portfolio",
                str(portfolio_path),
                "--strict",
            ]
        )

    assert exc.value.code == 1