"""
Audit the current portfolio configuration.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_audit_service import (
    PortfolioConfigurationAuditService,
)


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    portfolio = CurrentPortfolioLoader.load(
        options.portfolio
    )
    result = (
        PortfolioConfigurationAuditService()
        .audit(
            portfolio
        )
    )

    if options.json:
        print(
            json.dumps(
                result.to_dict(),
                indent=2,
                allow_nan=False,
            )
        )
    else:
        print_audit_result(
            result
        )

    if options.strict and not result.is_market_data_ready:
        raise SystemExit(1)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate current portfolio configuration and "
            "check market-data readiness."
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the audit result as JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit with code 1 unless every holding is ready "
            "for market-price lookup."
        ),
    )

    return parser


def print_audit_result(
    result,
) -> None:
    print()
    print("=" * 92)
    print("Current Portfolio Configuration Audit")
    print("=" * 92)
    print(
        f"Portfolio              : "
        f"{result.portfolio_name}"
    )
    print(
        f"Holdings               : "
        f"{result.holding_count}"
    )
    print(
        f"Market-data ready      : "
        f"{result.market_data_ready_count}"
    )
    print(
        f"Configuration valid    : "
        f"{'YES' if result.is_valid else 'NO'}"
    )
    print(
        f"Market-data ready      : "
        f"{'YES' if result.is_market_data_ready else 'NO'}"
    )
    print(
        f"Errors / Warnings / Info: "
        f"{result.error_count} / "
        f"{result.warning_count} / "
        f"{result.info_count}"
    )

    if not result.issues:
        print("-" * 92)
        print("No configuration issues found.")
        return

    print("-" * 92)
    print(
        f"{'Level':<10}"
        f"{'Code':<34}"
        f"{'Symbol':<12}"
        f"Message"
    )
    print("-" * 92)

    for issue in result.issues:
        print(
            f"{issue.level:<10}"
            f"{issue.code:<34}"
            f"{(issue.symbol or '-'): <12}"
            f"{issue.message}"
        )


if __name__ == "__main__":
    main()