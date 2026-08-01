"""
Inspect the current portfolio and calculated snapshot.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_snapshot_service import (
    PortfolioSnapshotService,
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

    print_snapshot(
        snapshot
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and display the current investment portfolio."
        ),
    )
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=CurrentPortfolioLoader.DEFAULT_PATH,
        help=(
            "Path to the current portfolio JSON file. "
            "Default: %(default)s."
        ),
    )

    return parser


def print_snapshot(
    snapshot,
) -> None:
    print()
    print("=" * 84)
    print("Current Portfolio Snapshot")
    print("=" * 84)
    print(
        f"Portfolio            : "
        f"{snapshot.portfolio_name}"
    )
    print(
        f"Base currency        : "
        f"{snapshot.base_currency}"
    )
    print(
        f"Total value          : "
        f"{snapshot.total_value:,.2f}"
    )
    print(
        f"Invested             : "
        f"{snapshot.invested_value:,.2f} "
        f"({snapshot.invested_weight * 100:.2f}%)"
    )
    print(
        f"Cash                 : "
        f"{snapshot.cash_value:,.2f} "
        f"({snapshot.cash_weight * 100:.2f}%)"
    )
    print(
        f"Monthly contribution : "
        f"{snapshot.monthly_contribution:,.2f}"
    )

    print("-" * 84)
    print("Asset breakdown")
    print("-" * 84)
    print(
        f"{'Asset':<20}"
        f"{'Amount':>20}"
        f"{'Weight':>20}"
    )

    for item in snapshot.asset_breakdown:
        print(
            f"{item.key:<20}"
            f"{item.amount:>20,.2f}"
            f"{item.percent:>19.2f}%"
        )

    print("-" * 84)
    print("Sleeve breakdown")
    print("-" * 84)
    print(
        f"{'Sleeve':<20}"
        f"{'Amount':>20}"
        f"{'Weight':>20}"
    )

    for item in snapshot.sleeve_breakdown:
        print(
            f"{item.key:<20}"
            f"{item.amount:>20,.2f}"
            f"{item.percent:>19.2f}%"
        )


if __name__ == "__main__":
    main()