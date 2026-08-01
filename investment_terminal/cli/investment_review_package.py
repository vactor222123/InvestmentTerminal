"""
Generate a first unified investment review package skeleton.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
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

    warnings = (
        "ETF analysis is not integrated yet.",
        "Watchlist analysis is not integrated yet.",
        "News and geopolitical context must be added externally.",
    )

    package = InvestmentReviewPackageBuilder().build(
        portfolio_name=portfolio.name,
        data_freshness={
            "status": "NOT_CONNECTED",
            "message": (
                "Freshness data will be connected to the market "
                "data pipeline in a later sprint."
            ),
        },
        market_analysis={
            "status": "NOT_CONNECTED",
            "message": (
                "Market ranking output is not connected yet."
            ),
        },
        portfolio=snapshot.to_dict(),
        stock_analysis={
            "status": "NOT_CONNECTED",
            "items": [],
        },
        etf_analysis={
            "status": "NOT_CONNECTED",
            "items": [],
        },
        watchlist={
            "status": "NOT_CONNECTED",
            "items": [],
        },
        opportunities={
            "status": "NOT_CONNECTED",
            "items": [],
        },
        machine_recommendations={
            "status": "NOT_CONNECTED",
            "items": [],
        },
        generated_at=datetime.now(timezone.utc),
        warnings=warnings,
    )

    output = InvestmentReviewPackageExporter().export(
        package,
        options.output,
    )

    if options.print_json:
        print(
            json.dumps(
                package.to_dict(),
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
        f"Portfolio : {package.portfolio_name}"
    )
    print(
        f"Generated : {package.generated_at.isoformat()}"
    )
    print(
        f"Sections  : {len(package.sections)}"
    )
    print(
        f"Warnings  : {len(package.warnings)}"
    )
    print(
        f"Output    : {output}"
    )


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