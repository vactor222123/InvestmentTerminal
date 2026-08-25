"""CLI for parse-only qualification of one private transaction CSV."""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.portfolio.transaction_csv_qualification import (
    TransactionCsvQualificationService,
    TransactionCsvQualificationStatus,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must be timezone-aware")
    return parsed


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Qualify one transaction CSV without persistence."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--qualified-at", type=_aware_datetime, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None, *, clock=None) -> None:
    options = build_argument_parser().parse_args(argv)
    result = TransactionCsvQualificationService(
        clock=clock or (lambda: datetime.now(timezone.utc))
    ).qualify(options.input, qualified_at=options.qualified_at)
    payload = result.to_dict()
    write_json_atomic(options.output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print("Transaction CSV Qualification")
        print(f"Status       : {result.status.value}")
        print(f"Transactions : {result.transaction_count}")
        print(f"Duration     : {result.duration_seconds} seconds")
        print(f"Report       : {options.output}")
    if result.status is TransactionCsvQualificationStatus.FAILED:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
