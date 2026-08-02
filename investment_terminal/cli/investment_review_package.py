"""
Generate the unified investment review package.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_market_value_service import (
    PortfolioMarketValueService,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
)
from investment_terminal.portfolio.portfolio_quote_json_provider import (
    JsonPortfolioPriceProvider,
)
from investment_terminal.review.portfolio_analysis_package_loader import (
    PortfolioAnalysisPackageLoader,
)
from investment_terminal.review.portfolio_analysis_review_adapter import (
    PortfolioAnalysisReviewAdapter,
)
from investment_terminal.review.portfolio_review_adapter import (
    PortfolioReviewAdapter,
)
from investment_terminal.review.review_package_builder import (
    InvestmentReviewPackageBuilder,
)
from investment_terminal.review.review_package_exporter import (
    InvestmentReviewPackageExporter,
)


DEFAULT_OUTPUT = (
    Path("output")
    / "investment_review_package.json"
)
DEFAULT_STOCK_ANALYSIS = (
    Path("output")
    / "us_large_cap_30_portfolio.json"
)
DEFAULT_PORTFOLIO_QUOTES = (
    Path("data")
    / "portfolios"
    / "portfolio_quotes.json"
)


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    portfolio = CurrentPortfolioLoader.load(
        options.portfolio
    )
    snapshot = PortfolioSnapshotService().build(
        portfolio
    )
    market_value = load_portfolio_market_value(
        portfolio=portfolio,
        quotes_path=options.portfolio_quotes,
    )

    integrated = load_stock_analysis(
        options.stock_analysis
    )
    warnings = build_warnings(
        stock_analysis_connected=(
            integrated is not None
        ),
        portfolio_market_value_connected=(
            market_value is not None
        ),
    )

    if integrated is None:
        sections = disconnected_stock_sections()
    else:
        sections = (
            PortfolioAnalysisReviewAdapter()
            .adapt(
                integrated
            )
        )

    package = InvestmentReviewPackageBuilder().build(
        portfolio_name=portfolio.name,
        data_freshness=sections[
            "data_freshness"
        ],
        market_analysis=sections[
            "market_analysis"
        ],
        portfolio={
            **PortfolioReviewAdapter().adapt(
                snapshot=snapshot,
                market_value=market_value,
                quotes_source=(
                    str(options.portfolio_quotes)
                    if market_value is not None
                    else None
                ),
            ),
            "stock_analysis_source": (
                str(options.stock_analysis)
                if integrated is not None
                else None
            ),
        },
        stock_analysis=sections[
            "stock_analysis"
        ],
        etf_analysis={
            "status": "NOT_CONNECTED",
            "items": [],
        },
        watchlist={
            "status": "NOT_CONNECTED",
            "items": [],
        },
        opportunities=sections[
            "opportunities"
        ],
        machine_recommendations=sections[
            "machine_recommendations"
        ],
        generated_at=datetime.now(
            timezone.utc
        ),
        warnings=warnings,
    )

    payload = package.to_dict()

    if integrated is not None:
        payload[
            "source_stock_analysis_package"
        ] = sections[
            "source_package"
        ]

    output = export_payload(
        payload,
        options.output,
    )

    if options.print_json:
        print(
            json.dumps(
                payload,
                indent=2,
                allow_nan=False,
            )
        )
        return

    print()
    print("=" * 88)
    print("Investment Review Package")
    print("=" * 88)
    print(
        f"Portfolio      : "
        f"{package.portfolio_name}"
    )
    print(
        f"Generated      : "
        f"{package.generated_at.isoformat()}"
    )
    print(
        f"Stock analysis : "
        f"{'CONNECTED' if integrated is not None else 'NOT CONNECTED'}"
    )
    print(
        f"Sections       : "
        f"{len(package.sections)}"
    )
    print(
        f"Warnings       : "
        f"{len(package.warnings)}"
    )
    print(
        f"Output         : "
        f"{output}"
    )


def load_stock_analysis(
    path: Path | None,
) -> dict | None:
    if path is None:
        return None

    if not path.exists():
        return None

    return PortfolioAnalysisPackageLoader.load(
        path
    )


def load_portfolio_market_value(
    *,
    portfolio,
    quotes_path: Path | None,
):
    """
    Load market values only when quotes cover every holding.

    Personal working quote files may be incomplete while the portfolio
    is being configured. In that case the review package must fall back
    to the cost-basis snapshot instead of failing completely.
    """
    if quotes_path is None:
        return None

    if not quotes_path.exists():
        return None

    try:
        provider = JsonPortfolioPriceProvider.load(
            quotes_path
        )

        return PortfolioMarketValueService(
            provider
        ).calculate(
            portfolio
        )
    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


def disconnected_stock_sections() -> dict:
    return {
        "data_freshness": {
            "status": "NOT_CONNECTED",
            "message": (
                "No stock-analysis package was supplied or found."
            ),
        },
        "market_analysis": {
            "status": "NOT_CONNECTED",
            "message": (
                "Market ranking output is not connected."
            ),
        },
        "stock_analysis": {
            "status": "NOT_CONNECTED",
            "items": [],
        },
        "opportunities": {
            "status": "NOT_CONNECTED",
            "items": [],
        },
        "machine_recommendations": {
            "status": "NOT_CONNECTED",
            "items": [],
        },
    }


def build_warnings(
    *,
    stock_analysis_connected: bool,
    portfolio_market_value_connected: bool,
) -> tuple[str, ...]:
    warnings = [
        "ETF analysis is not integrated yet.",
        "Watchlist analysis is not integrated yet.",
        "News and geopolitical context must be added externally.",
    ]

    if not portfolio_market_value_connected:
        warnings.insert(
            0,
            "Portfolio market prices are not connected.",
        )

    if not stock_analysis_connected:
        warnings.insert(
            0,
            "Stock market analysis is not connected.",
        )

    return tuple(
        warnings
    )


def export_payload(
    payload: dict,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the unified investment review package "
            "for later external analysis."
        ),
    )
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=CurrentPortfolioLoader.DEFAULT_PATH,
        help=(
            "Path to the current portfolio JSON. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--portfolio-quotes",
        type=Path,
        default=DEFAULT_PORTFOLIO_QUOTES,
        help=(
            "Optional JSON file with current portfolio quotes. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--stock-analysis",
        type=Path,
        default=DEFAULT_STOCK_ANALYSIS,
        help=(
            "Path to the exported stock portfolio-ranking JSON. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Output review-package JSON path. "
            "Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help=(
            "Print the generated package instead of the summary."
        ),
    )

    return parser


if __name__ == "__main__":
    main()