"""CLI for read-only offline quote qualification."""

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.portfolio.offline_quote_qualification import OfflineQuoteQualificationResult, OfflineQuoteQualificationService, OfflineQuoteQualificationStatus
from investment_terminal.portfolio.portfolio_quote_json_provider import JsonPortfolioPriceProvider
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import SQLitePortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_store import PortfolioTransactionSQLiteStore
from investment_terminal.utils.atomic_write import write_json_atomic


def _aware(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must be timezone-aware")
    return parsed


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Qualify offline quotes without valuation persistence.")
    value.add_argument("--transaction-database", type=Path, required=True)
    value.add_argument("--quotes", type=Path, required=True)
    value.add_argument("--ledger-id", required=True)
    value.add_argument("--portfolio-name", required=True)
    value.add_argument("--base-currency", required=True)
    value.add_argument("--valued-at", type=_aware, required=True)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(argv: Sequence[str] | None = None, *, clock=None) -> int:
    o = parser().parse_args(argv)
    repository = SQLitePortfolioTransactionRepository(PortfolioTransactionSQLiteStore(
        o.transaction_database, ledger_id=o.ledger_id,
        portfolio_name=o.portfolio_name, base_currency=o.base_currency))
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        provider = JsonPortfolioPriceProvider.load(o.quotes)
        result = OfflineQuoteQualificationService(
            repository, provider, clock=runtime_clock
        ).qualify(valued_at=o.valued_at)
    except Exception as exc:
        started = runtime_clock()
        result = OfflineQuoteQualificationResult(
            OfflineQuoteQualificationStatus.FAILED, o.valued_at, started,
            runtime_clock(), failure={"type": type(exc).__name__,
                                      "reason": "offline quote qualification failed"}
        )
    payload = result.to_dict()
    write_json_atomic(o.output, payload)
    if o.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print("Offline Quote Qualification")
        print(f"Status   : {result.status.value}")
        print(f"Required : {result.required_quote_count}")
        print(f"Matched  : {result.matched_quote_count}")
    return 0 if result.status is OfflineQuoteQualificationStatus.SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
