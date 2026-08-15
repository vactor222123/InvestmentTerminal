"""
Read-only command-line inspection for the provider usage/cost ledger.
"""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime
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


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "must be an ISO-8601 datetime"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError(
            "must be timezone-aware"
        )
    return parsed


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

    recent = subparsers.add_parser(
        "recent",
        help="List the newest bounded provider usage/cost records.",
    )
    recent.add_argument(
        "--limit",
        type=int,
        required=True,
    )

    between = subparsers.add_parser(
        "between",
        help="List records in the half-open [started-at, ended-at) window.",
    )
    between.add_argument(
        "--started-at",
        type=_aware_datetime,
        required=True,
    )
    between.add_argument(
        "--ended-at",
        type=_aware_datetime,
        required=True,
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


def _records_report(
    command: str,
    records,
) -> dict[str, Any]:
    return {
        "command": command,
        "count": len(records),
        "records": [
            record.to_dict()
            for record in records
        ],
    }


def _build_report(
    options: argparse.Namespace,
    *,
    repository: SQLiteGroundedProviderUsageCostLedgerRepository,
) -> dict[str, Any]:
    if options.command == "list":
        return _records_report(
            "list",
            repository.list_all(),
        )

    if options.command == "recent":
        return _records_report(
            "recent",
            repository.list_recent(
                options.limit
            ),
        )

    if options.command == "between":
        return _records_report(
            "between",
            repository.list_between(
                options.started_at,
                options.ended_at,
            ),
        )

    if options.command == "show":
        record = repository.require(
            options.request_id
        )
        return {
            "command": "show",
            "record": record.to_dict(),
        }

    if options.command == "summary":
        summary = repository.summarize()
        return {
            "command": "summary",
            **summary.to_dict(),
        }

    raise RuntimeError(
        f"Unhandled provider usage/cost command: {options.command}"
    )


def _print_human(
    command: str,
    report: dict[str, Any],
) -> None:
    print("Provider Usage/Cost Ledger")

    if command in {
        "list",
        "recent",
        "between",
    }:
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
        print(f"Requests     : {report['request_count']}")
        print(f"Currency     : {report['currency'] or 'none'}")
        print(f"Input tokens : {report['input_tokens']}")
        print(f"Output tokens: {report['output_tokens']}")
        print(f"Total tokens : {report['total_tokens']}")
        print(f"Input cost   : {report['input_cost']}")
        print(f"Output cost  : {report['output_cost']}")
        print(f"Total cost   : {report['total_cost']}")
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
