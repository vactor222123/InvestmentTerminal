"""
Read-only command-line inspection for the provider usage/cost ledger.
"""

import argparse
import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from investment_terminal.ai.providers.usage_ledger_sqlite_repository import (
    SQLiteGroundedProviderUsageCostLedgerRepository,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)


DEFAULT_DATABASE = (
    Path("data")
    / "knowledge"
    / "provider_usage_cost.db"
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect persistent provider usage/cost records without mutating "
            "the ledger."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Provider usage/cost SQLite database. Default: %(default)s.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print complete JSON output.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )
    subparsers.add_parser(
        "list",
        help="List all provider usage/cost records.",
    )

    show = subparsers.add_parser(
        "show",
        help="Show one exact request record.",
    )
    show.add_argument(
        "--request-id",
        required=True,
    )

    subparsers.add_parser(
        "summary",
        help="Summarize durable provider usage and cost totals.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    if not options.database.is_file():
        parser.error(
            "Provider usage/cost database does not exist: "
            f"{options.database}"
        )

    repository = SQLiteGroundedProviderUsageCostLedgerRepository(
        GroundedProviderUsageCostLedgerSQLiteStore(
            options.database
        )
    )

    try:
        report = _build_report(
            options,
            repository=repository,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(str(exc))

    if options.json:
        print(
            json.dumps(
                report,
                indent=2,
                allow_nan=False,
            )
        )
        return

    _print_human(
        options.command,
        report,
    )


def _build_report(
    options: argparse.Namespace,
    *,
    repository: SQLiteGroundedProviderUsageCostLedgerRepository,
) -> dict[str, Any]:
    if options.command == "list":
        records = repository.list_all()
        return {
            "command": "list",
            "count": len(records),
            "records": [
                record.to_dict()
                for record in records
            ],
        }

    if options.command == "show":
        record = repository.require(
            options.request_id
        )
        return {
            "command": "show",
            "record": record.to_dict(),
        }

    if options.command == "summary":
        records = repository.list_all()
        currencies = {
            record.currency
            for record in records
        }
        if len(currencies) > 1:
            raise RuntimeError(
                "summary requires one currency across ledger records"
            )

        input_tokens = sum(
            record.input_tokens
            for record in records
        )
        output_tokens = sum(
            record.output_tokens
            for record in records
        )
        total_tokens = sum(
            record.total_tokens
            for record in records
        )
        input_cost = sum(
            (
                record.input_cost
                for record in records
            ),
            Decimal("0"),
        )
        output_cost = sum(
            (
                record.output_cost
                for record in records
            ),
            Decimal("0"),
        )
        total_cost = sum(
            (
                record.total_cost
                for record in records
            ),
            Decimal("0"),
        )
        return {
            "command": "summary",
            "request_count": len(records),
            "currency": (
                next(iter(currencies))
                if currencies
                else None
            ),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost": str(input_cost),
            "output_cost": str(output_cost),
            "total_cost": str(total_cost),
        }

    raise RuntimeError(
        f"Unhandled provider usage/cost command: {options.command}"
    )


def _print_human(
    command: str,
    report: dict[str, Any],
) -> None:
    print("Provider Usage/Cost Ledger")

    if command == "list":
        print(
            f"Records      : {report['count']}"
        )
        for record in report["records"]:
            _print_record(record)
        return

    if command == "show":
        _print_record(
            report["record"]
        )
        return

    if command == "summary":
        print(
            f"Requests     : {report['request_count']}"
        )
        print(
            f"Currency     : {report['currency'] or 'none'}"
        )
        print(
            f"Input tokens : {report['input_tokens']}"
        )
        print(
            f"Output tokens: {report['output_tokens']}"
        )
        print(
            f"Total tokens : {report['total_tokens']}"
        )
        print(
            f"Input cost   : {report['input_cost']}"
        )
        print(
            f"Output cost  : {report['output_cost']}"
        )
        print(
            f"Total cost   : {report['total_cost']}"
        )
        return

    raise RuntimeError(
        f"Unhandled human output command: {command}"
    )


def _print_record(
    record: dict[str, Any],
) -> None:
    print(
        "  "
        f"{record['request_id']} "
        f"provider={record['provider_identity']} "
        f"model={record['model_identity']}"
    )
    print(
        "    "
        f"tokens={record['input_tokens']}+"
        f"{record['output_tokens']}="
        f"{record['total_tokens']}"
    )
    print(
        "    "
        f"cost={record['total_cost']} "
        f"{record['currency']} "
        f"recorded_at={record['recorded_at']}"
    )


if __name__ == "__main__":
    main()
