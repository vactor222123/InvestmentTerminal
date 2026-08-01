"""
Import exact holdings from CSV into the current portfolio JSON.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.current_portfolio_writer import (
    CurrentPortfolioWriter,
)
from investment_terminal.portfolio.portfolio_holding_csv_importer import (
    PortfolioHoldingCsvImporter,
)


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    result = PortfolioHoldingCsvImporter.load(
        options.csv
    )

    if options.preview:
        print(
            json.dumps(
                result.to_dict(),
                indent=2,
                allow_nan=False,
            )
        )
        return

    output = CurrentPortfolioWriter.replace_holdings(
        portfolio_path=options.portfolio,
        import_result=result,
        output_path=options.output,
    )

    print()
    print("=" * 84)
    print("Portfolio Holdings Import")
    print("=" * 84)
    print(
        f"Source CSV     : {options.csv}"
    )
    print(
        f"Holdings       : {result.count}"
    )
    print(
        f"Total cost     : {result.total_cost:,.2f}"
    )
    print(
        f"Written to     : {output}"
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate portfolio holdings from CSV and write them "
            "into the current portfolio JSON."
        ),
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to the portfolio holdings CSV file.",
    )
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=CurrentPortfolioLoader.DEFAULT_PATH,
        help=(
            "Existing portfolio JSON whose policy and cash balance "
            "will be preserved. Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Optional output JSON path. Without this option, the "
            "portfolio file is updated in place."
        ),
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help=(
            "Validate and print imported holdings without writing."
        ),
    )

    return parser


if __name__ == "__main__":
    main()