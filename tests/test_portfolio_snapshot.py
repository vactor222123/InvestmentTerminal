"""
Tests for portfolio snapshot calculation and CLI.
"""

from pathlib import Path

import pytest

from investment_terminal.cli.current_portfolio import (
    main,
)
from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
)


def create_portfolio() -> CurrentPortfolio:
    return CurrentPortfolio(
        name="Test Portfolio",
        policy=PortfolioPolicy(
            core_target_weight=0.85,
            tactical_target_weight=0.10,
            cash_target_weight=0.05,
            monthly_contribution=2000.0,
            base_currency="EUR",
        ),
        holdings=(
            PortfolioHolding(
                symbol="IWDA",
                name="MSCI World ETF",
                asset_type="ETF",
                sleeve="CORE",
                quantity=100.0,
                average_cost=100.0,
                isin="IE00B4L5Y983",
                exchange_ticker="IWDA",
            ),
            PortfolioHolding(
                symbol="AGGH",
                name="Global Aggregate Bond ETF",
                asset_type="BOND",
                sleeve="CORE",
                quantity=50.0,
                average_cost=100.0,
                isin="IE00BDBRDM35",
                exchange_ticker="AGGH",
            ),
            PortfolioHolding(
                symbol="MSFT",
                name="Microsoft",
                asset_type="STOCK",
                sleeve="TACTICAL",
                quantity=2.0,
                average_cost=500.0,
            ),
        ),
        cash_balance=4000.0,
    )


def test_snapshot_calculates_total_values() -> None:
    snapshot = PortfolioSnapshotService().build(
        create_portfolio()
    )

    assert snapshot.invested_value == 16000.0
    assert snapshot.cash_value == 4000.0
    assert snapshot.total_value == 20000.0
    assert snapshot.invested_weight == 0.80
    assert snapshot.cash_weight == 0.20


def test_snapshot_calculates_asset_breakdown() -> None:
    snapshot = PortfolioSnapshotService().build(
        create_portfolio()
    )

    assert snapshot.asset("ETF").amount == 10000.0
    assert snapshot.asset("ETF").weight == 0.50
    assert snapshot.asset("BOND").weight == 0.25
    assert snapshot.asset("STOCK").weight == 0.05
    assert snapshot.asset("CASH").weight == 0.20


def test_snapshot_calculates_sleeve_breakdown() -> None:
    snapshot = PortfolioSnapshotService().build(
        create_portfolio()
    )

    assert snapshot.sleeve("CORE").amount == 15000.0
    assert snapshot.sleeve("CORE").weight == 0.75
    assert snapshot.sleeve("TACTICAL").weight == 0.05
    assert snapshot.sleeve("RESERVE").weight == 0.20


def test_snapshot_supports_empty_portfolio() -> None:
    portfolio = CurrentPortfolio(
        name="Empty",
        policy=create_portfolio().policy,
        holdings=(),
        cash_balance=0.0,
    )

    snapshot = PortfolioSnapshotService().build(
        portfolio
    )

    assert snapshot.total_value == 0.0
    assert snapshot.invested_weight == 0.0
    assert snapshot.cash_weight == 0.0
    assert all(
        item.weight == 0.0
        for item in snapshot.asset_breakdown
    )


def test_snapshot_rejects_invalid_portfolio() -> None:
    with pytest.raises(
        TypeError,
        match="CurrentPortfolio",
    ):
        PortfolioSnapshotService().build(
            None
        )


def test_cli_prints_default_portfolio(
    capsys,
) -> None:
    main([])

    output = capsys.readouterr().out

    assert "Current Portfolio Snapshot" in output
    assert "Viktor Investment Portfolio" in output
    assert "1,600.00" in output
    assert "RESERVE" in output


def test_cli_accepts_custom_portfolio(
    tmp_path: Path,
    capsys,
) -> None:
    path = (
        tmp_path
        / "portfolio.json"
    )
    path.write_text(
        """{
          "name": "Custom",
          "policy": {
            "core_target_weight": 0.85,
            "tactical_target_weight": 0.10,
            "cash_target_weight": 0.05,
            "monthly_contribution": 1500.0,
            "base_currency": "EUR"
          },
          "cash_balance": 500.0,
          "holdings": []
        }""",
        encoding="utf-8",
    )

    main(
        [
            "--portfolio",
            str(path),
        ]
    )

    output = capsys.readouterr().out

    assert "Custom" in output
    assert "500.00" in output
    assert "1,500.00" in output