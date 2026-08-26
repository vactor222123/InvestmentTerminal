"""CLI for bounded OpenFIGI instrument-metadata bootstrap."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from investment_terminal.portfolio.openfigi_metadata_bootstrap import (
    OpenFigiBootstrapFailure,
    OpenFigiHttpClient,
    OpenFigiMetadataBootstrapService,
    bootstrap_report,
)
from investment_terminal.portfolio.portfolio_quote_json_provider import JsonPortfolioPriceProvider
from investment_terminal.portfolio.position_reconstruction import PositionReconstructor
from investment_terminal.portfolio.transaction_ledger_sqlite_repository import SQLitePortfolioTransactionRepository
from investment_terminal.portfolio.transaction_ledger_sqlite_store import PortfolioTransactionSQLiteStore
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Bootstrap private metadata from OpenFIGI v3.")
    value.add_argument("--transaction-database", type=Path, required=True)
    value.add_argument("--quotes", type=Path, required=True)
    value.add_argument("--ledger-id", required=True)
    value.add_argument("--portfolio-name", required=True)
    value.add_argument("--base-currency", required=True)
    value.add_argument("--run-id", required=True)
    value.add_argument("--response-archive", type=Path, required=True)
    value.add_argument("--metadata-output", type=Path, required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--timeout-seconds", type=float, default=30.0)
    value.add_argument("--json", action="store_true")
    return value


def main(argv: Sequence[str] | None = None, *, client=None, clock=None) -> int:
    options = parser().parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    started = runtime_clock()
    counts: list[int | None] = [None] * 4
    try:
        if not options.transaction_database.is_file():
            raise FileNotFoundError("Transaction database does not exist")
        repository = SQLitePortfolioTransactionRepository(PortfolioTransactionSQLiteStore(
            options.transaction_database, ledger_id=options.ledger_id,
            portfolio_name=options.portfolio_name, base_currency=options.base_currency,
        ))
        reconstruction = PositionReconstructor.reconstruct(repository.snapshot())
        provider = JsonPortfolioPriceProvider.load(options.quotes)
        active_client = client or OpenFigiHttpClient(
            api_key=os.environ.get("OPENFIGI_API_KEY"),
            timeout_seconds=options.timeout_seconds,
        )
        result = OpenFigiMetadataBootstrapService(
            active_client, batch_size=100 if os.environ.get("OPENFIGI_API_KEY") else 5
        ).bootstrap(
            reconstruction, provider, retrieved_at=started, run_id=options.run_id,
            archive_directory=options.response_archive,
            metadata_output=options.metadata_output,
        )
        counts = [result.requested_count, result.matched_count,
                  result.batch_count, result.archived_response_count]
        status = "SUCCESS"
        failure_type = None
    except Exception as exc:
        status = "FAILED"
        failure_type = type(exc).__name__
        if isinstance(exc, OpenFigiBootstrapFailure):
            counts = [exc.requested_count, None, exc.batch_count,
                      exc.archived_response_count]
    completed = runtime_clock()
    payload = bootstrap_report(
        status=status, started_at=started, completed_at=completed,
        requested_count=counts[0], matched_count=counts[1],
        batch_count=counts[2], archived_response_count=counts[3],
        failure_type=failure_type,
    )
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print(f"OpenFIGI Metadata Bootstrap: {status}")
    return 0 if status == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
