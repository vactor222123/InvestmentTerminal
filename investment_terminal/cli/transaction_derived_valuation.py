"""CLI for one bounded transaction-derived valuation."""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.portfolio.portfolio_quote_json_provider import JsonPortfolioPriceProvider
from investment_terminal.portfolio.portfolio_valuation_history_sqlite_repository import SQLitePortfolioValuationHistoryRepository
from investment_terminal.portfolio.portfolio_valuation_history_sqlite_store import PortfolioValuationHistorySQLiteStore
from investment_terminal.portfolio.transaction_derived_valuation import TransactionDerivedValuationService, TransactionDerivedValuationStatus
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import SQLitePortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_store import PortfolioTransactionSQLiteStore
from investment_terminal.utils.atomic_write import write_json_atomic


class ValuationReportAfterCommitError(RuntimeError):
    """Valuation committed, but its redacted report was not replaced."""


def _aware(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must be timezone-aware")
    return parsed


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append one transaction-derived valuation snapshot.")
    parser.add_argument("--transaction-database", type=Path, required=True)
    parser.add_argument("--quotes", type=Path, required=True)
    parser.add_argument("--valuation-database", type=Path, required=True)
    parser.add_argument("--ledger-id", required=True)
    parser.add_argument("--portfolio-name", required=True)
    parser.add_argument("--base-currency", required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--valued-at", type=_aware, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None, *, clock=None) -> int:
    o = build_argument_parser().parse_args(argv)
    transactions = SQLitePortfolioTransactionRepository(PortfolioTransactionSQLiteStore(
        o.transaction_database, ledger_id=o.ledger_id, portfolio_name=o.portfolio_name,
        base_currency=o.base_currency))
    valuations = SQLitePortfolioValuationHistoryRepository(PortfolioValuationHistorySQLiteStore(
        o.valuation_database, ledger_id=o.ledger_id, portfolio_name=o.portfolio_name))
    result = TransactionDerivedValuationService(
        transactions, valuations, JsonPortfolioPriceProvider.load(o.quotes),
        clock=clock or (lambda: datetime.now(timezone.utc))).run(
            snapshot_id=o.snapshot_id, valued_at=o.valued_at)
    payload = result.to_dict()
    try:
        write_json_atomic(o.output, payload)
    except Exception as exc:
        if result.status is TransactionDerivedValuationStatus.SUCCESS:
            raise ValuationReportAfterCommitError(
                "valuation committed but redacted report write failed; inspect the valuation store before retrying"
            ) from exc
        raise RuntimeError("valuation failed and redacted report write failed") from exc
    if o.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print("Transaction-Derived Valuation")
        print(f"Status    : {result.status.value}")
        print(f"Positions : {result.open_position_count}")
        print(f"Stored    : {result.stored_snapshot_total}")
    return 0 if result.status is TransactionDerivedValuationStatus.SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
