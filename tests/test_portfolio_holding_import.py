"""
Tests for portfolio holding CSV import.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.import_portfolio_holdings import (
    main,
)
from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.current_portfolio_writer import (
    CurrentPortfolioWriter,
)
from investment_terminal.portfolio.portfolio_holding_csv_importer import (
    PortfolioHoldingCsvImporter,
)


def write_valid_csv(
    path: Path,
) -> None:
    path.write_text(
        """symbol,name,asset_type,sleeve,quantity,average_cost,currency,isin,exchange_ticker
WORLD,World ETF,ETF,CORE,10.5,100.25,EUR,IE00B4L5Y983,IWDA
MSFT,Microsoft,STOCK,TACTICAL,2,400,EUR,,MSFT
""",
        encoding="utf-8",
    )


def write_portfolio_json(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "name": "Test Portfolio",
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


def test_csv_importer_loads_holdings(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "holdings.csv"
    )
    write_valid_csv(
        path
    )

    result = PortfolioHoldingCsvImporter.load(
        path
    )

    assert result.count == 2
    assert result.holdings[0].isin == (
        "IE00B4L5Y983"
    )
    assert result.holdings[1].exchange_ticker == (
        "MSFT"
    )
    assert result.total_cost == 1852.63


def test_csv_importer_accepts_decimal_comma(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "holdings.csv"
    )
    path.write_text(
        """symbol,name,asset_type,sleeve,quantity,average_cost,currency,isin,exchange_ticker
WORLD,World ETF,ETF,CORE,"10,5","100,25",EUR,IE00B4L5Y983,IWDA
""",
        encoding="utf-8",
    )

    result = PortfolioHoldingCsvImporter.load(
        path
    )

    assert result.holdings[0].quantity == 10.5
    assert result.holdings[0].average_cost == 100.25


def test_csv_importer_reports_line_number(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "holdings.csv"
    )
    path.write_text(
        """symbol,name,asset_type,sleeve,quantity,average_cost,currency,isin,exchange_ticker
WORLD,World ETF,ETF,CORE,abc,100,EUR,IE00B4L5Y983,IWDA
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="CSV line 2",
    ):
        PortfolioHoldingCsvImporter.load(
            path
        )


def test_writer_preserves_policy_and_cash(
    tmp_path: Path,
) -> None:
    csv_path = (
        tmp_path
        / "holdings.csv"
    )
    portfolio_path = (
        tmp_path
        / "portfolio.json"
    )
    output_path = (
        tmp_path
        / "updated.json"
    )

    write_valid_csv(
        csv_path
    )
    write_portfolio_json(
        portfolio_path
    )

    result = PortfolioHoldingCsvImporter.load(
        csv_path
    )
    CurrentPortfolioWriter.replace_holdings(
        portfolio_path=portfolio_path,
        import_result=result,
        output_path=output_path,
    )

    portfolio = CurrentPortfolioLoader.load(
        output_path
    )

    assert len(portfolio.holdings) == 2
    assert portfolio.cash_balance == 1600.0
    assert portfolio.policy.monthly_contribution == 2000.0


def test_cli_preview_does_not_write(
    tmp_path: Path,
    capsys,
) -> None:
    csv_path = (
        tmp_path
        / "holdings.csv"
    )
    write_valid_csv(
        csv_path
    )

    main(
        [
            "--csv",
            str(csv_path),
            "--preview",
        ]
    )

    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload["count"] == 2
    assert payload["holdings"][0]["symbol"] == (
        "WORLD"
    )


def test_cli_writes_output(
    tmp_path: Path,
    capsys,
) -> None:
    csv_path = (
        tmp_path
        / "holdings.csv"
    )
    portfolio_path = (
        tmp_path
        / "portfolio.json"
    )
    output_path = (
        tmp_path
        / "updated.json"
    )

    write_valid_csv(
        csv_path
    )
    write_portfolio_json(
        portfolio_path
    )

    main(
        [
            "--csv",
            str(csv_path),
            "--portfolio",
            str(portfolio_path),
            "--output",
            str(output_path),
        ]
    )

    output = capsys.readouterr().out

    assert output_path.exists()
    assert "Holdings       : 2" in output