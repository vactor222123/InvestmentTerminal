"""
Tests for portfolio strategy loading from JSON and CSV.
"""

import json
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_holding_csv_importer import (
    PortfolioHoldingCsvImporter,
)


def test_json_loader_reads_explicit_position_trade(
    tmp_path: Path,
) -> None:
    path = tmp_path / "portfolio.json"
    path.write_text(
        json.dumps(
            {
                "name": "Test",
                "policy": {
                    "core_target_weight": 0.80,
                    "tactical_target_weight": 0.10,
                    "cash_target_weight": 0.10,
                    "monthly_contribution": 2000.0,
                    "base_currency": "EUR"
                },
                "cash_balance": 1000.0,
                "holdings": [
                    {
                        "symbol": "TSLA",
                        "name": "Tesla",
                        "asset_type": "STOCK",
                        "sleeve": "TACTICAL",
                        "quantity": 2.0,
                        "average_cost": 250.0,
                        "currency": "EUR",
                        "isin": None,
                        "exchange_ticker": "TSLA",
                        "strategy": "POSITION_TRADE"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    portfolio = CurrentPortfolioLoader.load(path)

    assert portfolio.holdings[0].strategy == (
        "POSITION_TRADE"
    )


def test_json_loader_keeps_backwards_compatibility(
    tmp_path: Path,
) -> None:
    path = tmp_path / "portfolio.json"
    path.write_text(
        json.dumps(
            {
                "name": "Test",
                "policy": {
                    "core_target_weight": 0.80,
                    "tactical_target_weight": 0.10,
                    "cash_target_weight": 0.10,
                    "monthly_contribution": 2000.0,
                    "base_currency": "EUR"
                },
                "cash_balance": 1000.0,
                "holdings": [
                    {
                        "symbol": "MSFT",
                        "name": "Microsoft",
                        "asset_type": "STOCK",
                        "sleeve": "TACTICAL",
                        "quantity": 1.0,
                        "average_cost": 400.0,
                        "currency": "EUR",
                        "isin": None,
                        "exchange_ticker": "MSFT"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    portfolio = CurrentPortfolioLoader.load(path)

    assert portfolio.holdings[0].strategy == (
        "STOCK_LONG_TERM"
    )


def test_csv_importer_reads_strategy_column(
    tmp_path: Path,
) -> None:
    path = tmp_path / "holdings.csv"
    path.write_text(
        """symbol,name,asset_type,sleeve,quantity,average_cost,currency,isin,exchange_ticker,strategy
TSLA,Tesla,STOCK,TACTICAL,2,250,EUR,,TSLA,POSITION_TRADE
""",
        encoding="utf-8",
    )

    result = PortfolioHoldingCsvImporter.load(path)

    assert result.holdings[0].strategy == (
        "POSITION_TRADE"
    )


def test_csv_importer_accepts_legacy_header(
    tmp_path: Path,
) -> None:
    path = tmp_path / "holdings.csv"
    path.write_text(
        """symbol,name,asset_type,sleeve,quantity,average_cost,currency,isin,exchange_ticker
MSFT,Microsoft,STOCK,TACTICAL,1,400,EUR,,MSFT
""",
        encoding="utf-8",
    )

    result = PortfolioHoldingCsvImporter.load(path)

    assert result.holdings[0].strategy == (
        "STOCK_LONG_TERM"
    )