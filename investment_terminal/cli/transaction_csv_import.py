"""CLI for one bounded durable portfolio-transaction CSV import."""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.portfolio.transaction_csv_import import (
    TransactionCsvImportService,
    TransactionCsvImportStatus,
)
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import (
    SQLitePortfolioTransactionRepository,
)
from investment_terminal.portfolio.transaction_ledger_sqlite_store import (
    PortfolioTransactionSQLiteStore,
)
from investment_terminal.utils.atomic_write import write_json_atomic


class TransactionImportReportAfterCommitError(RuntimeError):
    """Import committed, but its redacted operational report was not replaced."""


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
        description="Atomically import one explicit portfolio-transaction CSV."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--ledger-id", required=True)
    parser.add_argument("--portfolio-name", required=True)
    parser.add_argument("--base-currency", required=True)
    parser.add_argument("--imported-at", type=_aware_datetime, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None, *, clock=None) -> int:
    options = build_argument_parser().parse_args(argv)
    repository = SQLitePortfolioTransactionRepository(
        PortfolioTransactionSQLiteStore(
            options.database,
            ledger_id=options.ledger_id,
            portfolio_name=options.portfolio_name,
            base_currency=options.base_currency,
        )
    )
    result = TransactionCsvImportService(
        repository,
        clock=clock or (lambda: datetime.now(timezone.utc)),
    ).import_csv(options.input, imported_at=options.imported_at)
    payload = result.to_dict()
    try:
        write_json_atomic(options.output, payload)
    except Exception as exc:
        if result.status is TransactionCsvImportStatus.SUCCESS:
            raise TransactionImportReportAfterCommitError(
                "transaction import committed but redacted report write failed; "
                "repair report output and rerun the exact input to reconcile"
            ) from exc
        raise RuntimeError(
            "transaction import did not commit and redacted report write failed"
        ) from exc
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print("Transaction CSV Import")
        print(f"Status     : {result.status.value}")
        print(f"Submitted  : {result.submitted_count}")
        print(f"Imported   : {result.imported_count}")
        print(f"Duplicates : {result.duplicate_count}")
    return 1 if result.status is TransactionCsvImportStatus.FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
