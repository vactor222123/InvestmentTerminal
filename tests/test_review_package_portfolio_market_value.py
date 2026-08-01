"""
Tests for portfolio market-value integration into the review package.
"""

import json
from pathlib import Path

from investment_terminal.cli.investment_review_package import (
    main,
)
from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_market_value_service import (
    PortfolioMarketValueService,
)
from investment_terminal.portfolio.portfolio_quote_json_provider import (
    JsonPortfolioPriceProvider,
)
from investment_terminal.review.portfolio_review_adapter import (
    PortfolioReviewAdapter,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
)


def write_portfolio(
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
                        "exchange_ticker": "IWDA"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def write_quotes(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "quotes": [
                    {
                        "instrument_key": "IE00B4L5Y983",
                        "exchange_ticker": "IWDA",
                        "price": 110.0,
                        "currency": "EUR",
                        "quoted_at": (
                            "2026-08-01T18:00:00+00:00"
                        ),
                        "source": "TEST"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_json_price_provider_loads_quote(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "quotes.json"
    )
    write_quotes(
        path
    )

    provider = JsonPortfolioPriceProvider.load(
        path
    )
    quote = provider.get_quote(
        instrument_key="IE00B4L5Y983",
        exchange_ticker="IWDA",
    )

    assert quote.price == 110.0
    assert quote.currency == "EUR"


def test_portfolio_review_adapter_connects_market_value(
    tmp_path: Path,
) -> None:
    portfolio_path = (
        tmp_path
        / "portfolio.json"
    )
    quotes_path = (
        tmp_path
        / "quotes.json"
    )
    write_portfolio(
        portfolio_path
    )
    write_quotes(
        quotes_path
    )

    portfolio = CurrentPortfolioLoader.load(
        portfolio_path
    )
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )
    market_value = PortfolioMarketValueService(
        JsonPortfolioPriceProvider.load(
            quotes_path
        )
    ).calculate(
        portfolio
    )

    payload = PortfolioReviewAdapter().adapt(
        snapshot=snapshot,
        market_value=market_value,
        quotes_source=str(
            quotes_path
        ),
    )

    assert payload["status"] == (
        "MARKET_VALUE_CONNECTED"
    )
    assert (
        payload["market_value"]
        ["total_market_value"]
        == 2700.0
    )


def test_cli_connects_portfolio_quotes(
    tmp_path: Path,
) -> None:
    portfolio_path = (
        tmp_path
        / "portfolio.json"
    )
    quotes_path = (
        tmp_path
        / "quotes.json"
    )
    output_path = (
        tmp_path
        / "review.json"
    )
    write_portfolio(
        portfolio_path
    )
    write_quotes(
        quotes_path
    )

    main(
        [
            "--portfolio",
            str(portfolio_path),
            "--portfolio-quotes",
            str(quotes_path),
            "--stock-analysis",
            str(
                tmp_path
                / "missing-stock.json"
            ),
            "--output",
            str(output_path),
        ]
    )

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8",
        )
    )
    section = payload[
        "sections"
    ][
        "portfolio"
    ]

    assert section["status"] == (
        "MARKET_VALUE_CONNECTED"
    )
    assert (
        section["market_value"]
        ["unrealized_profit_loss"]
        == 100.0
    )


def test_cli_falls_back_to_cost_basis_without_quotes(
    tmp_path: Path,
) -> None:
    portfolio_path = (
        tmp_path
        / "portfolio.json"
    )
    output_path = (
        tmp_path
        / "review.json"
    )
    write_portfolio(
        portfolio_path
    )

    main(
        [
            "--portfolio",
            str(portfolio_path),
            "--portfolio-quotes",
            str(
                tmp_path
                / "missing-quotes.json"
            ),
            "--stock-analysis",
            str(
                tmp_path
                / "missing-stock.json"
            ),
            "--output",
            str(output_path),
        ]
    )

    payload = json.loads(
        output_path.read_text(
            encoding="utf-8",
        )
    )
    section = payload[
        "sections"
    ][
        "portfolio"
    ]

    assert section["status"] == (
        "COST_BASIS_ONLY"
    )
    assert section["market_value"] is None