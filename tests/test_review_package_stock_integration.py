"""
Tests for stock-analysis integration into the review package.
"""

import json
from pathlib import Path

from investment_terminal.cli.investment_review_package import (
    main,
)
from investment_terminal.review.portfolio_analysis_package_loader import (
    PortfolioAnalysisPackageLoader,
)
from investment_terminal.review.portfolio_analysis_review_adapter import (
    PortfolioAnalysisReviewAdapter,
)


EXAMPLE_PORTFOLIO = Path(
    "data/portfolios/current_portfolio.example.json"
)


def create_stock_package(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.3",
                "generated_at": "2026-08-01T18:00:00+00:00",
                "universe": {
                    "name": "US Large Cap 30",
                    "size": 30
                },
                "market_data": {
                    "ready_count": 30,
                    "failed_count": 0,
                    "all_ready": True
                },
                "ranking": {
                    "candidates": [
                        {
                            "rank": 1,
                            "symbol": "GOOGL",
                            "overall_score": 83.0
                        },
                        {
                            "rank": 2,
                            "symbol": "JPM",
                            "overall_score": 78.0
                        }
                    ]
                },
                "recommendations": {
                    "recommendations": [
                        {
                            "rank": 1,
                            "symbol": "GOOGL",
                            "recommendation": "BUY"
                        },
                        {
                            "rank": 2,
                            "symbol": "JPM",
                            "recommendation": "WATCH"
                        }
                    ]
                },
                "investment_theses": {
                    "theses": [
                        {
                            "symbol": "GOOGL",
                            "headline": "Test thesis"
                        }
                    ]
                },
                "allocation": {
                    "positions": [
                        {
                            "symbol": "GOOGL",
                            "target_weight": 0.20
                        }
                    ],
                    "cash_weight": 0.10
                }
            }
        ),
        encoding="utf-8",
    )


def test_loader_reads_stock_package(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "stocks.json"
    )
    create_stock_package(
        path
    )

    payload = PortfolioAnalysisPackageLoader.load(
        path
    )

    assert payload["schema_version"] == "1.3"
    assert payload["universe"]["size"] == 30


def test_adapter_connects_required_sections(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "stocks.json"
    )
    create_stock_package(
        path
    )

    sections = (
        PortfolioAnalysisReviewAdapter()
        .adapt(
            PortfolioAnalysisPackageLoader.load(
                path
            )
        )
    )

    assert (
        sections["data_freshness"]["status"]
        == "CONNECTED"
    )
    assert (
        sections["stock_analysis"]["status"]
        == "CONNECTED"
    )
    assert (
        sections["machine_recommendations"]
        ["allocation"]["cash_weight"]
        == 0.10
    )


def test_adapter_extracts_buy_opportunities(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "stocks.json"
    )
    create_stock_package(
        path
    )

    sections = (
        PortfolioAnalysisReviewAdapter()
        .adapt(
            PortfolioAnalysisPackageLoader.load(
                path
            )
        )
    )

    assert len(
        sections["opportunities"]["items"]
    ) == 1
    assert (
        sections["opportunities"]["items"][0]
        ["symbol"]
        == "GOOGL"
    )


def test_cli_integrates_stock_package(
    tmp_path: Path,
    capsys,
) -> None:
    stock_path = (
        tmp_path
        / "stocks.json"
    )
    output_path = (
        tmp_path
        / "review.json"
    )
    create_stock_package(
        stock_path
    )

    main(
        [
            "--portfolio",
            str(EXAMPLE_PORTFOLIO),
            "--stock-analysis",
            str(stock_path),
            "--output",
            str(output_path),
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(
        output_path.read_text(
            encoding="utf-8",
        )
    )

    assert "Stock analysis : CONNECTED" in output
    assert (
        payload["sections"]["market_analysis"]
        ["status"]
        == "CONNECTED"
    )
    assert (
        payload["sections"]["opportunities"]
        ["items"][0]["symbol"]
        == "GOOGL"
    )
    assert (
        "source_stock_analysis_package"
        in payload
    )


def test_cli_falls_back_when_stock_package_missing(
    tmp_path: Path,
) -> None:
    output_path = (
        tmp_path
        / "review.json"
    )

    main(
        [
            "--portfolio",
            str(EXAMPLE_PORTFOLIO),
            "--stock-analysis",
            str(
                tmp_path
                / "missing.json"
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

    assert (
        payload["sections"]["stock_analysis"]
        ["status"]
        == "NOT_CONNECTED"
    )
