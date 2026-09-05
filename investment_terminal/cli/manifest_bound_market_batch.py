"""CLI for one manifest-bound resumable Yahoo market batch."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
    ManifestBoundMarketBatchService,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.services.historical_market_service import HistoricalMarketService
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Run one manifest-bound market batch.")
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--batch-index", type=int, required=True)
    value.add_argument("--checkpoint", type=Path, required=True)
    value.add_argument("--database", type=Path, required=True)
    value.add_argument("--cache-directory", type=Path, required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(
    argv: Sequence[str] | None = None,
    *,
    client=None,
    clock=None,
) -> int:
    options = parser().parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    database = None
    selection = None
    try:
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
        selection = ManifestBatchSelection.from_manifest(
            manifest,
            options.manifest_checksum,
            options.batch_index,
        )
        checkpoint = (
            json.loads(options.checkpoint.read_text(encoding="utf-8"))
            if options.checkpoint.exists()
            else None
        )
        database = Database(options.database)
        database.initialize()
        importer = HistoricalMarketService(
            client or YahooFinanceClient(cache_directory=options.cache_directory),
            CandleRepository(database),
        )
        payload = ManifestBoundMarketBatchService(
            importer=importer,
            checkpoint_writer=lambda value: write_json_atomic(
                options.checkpoint, value
            ),
            clock=runtime_clock,
        ).run(selection, checkpoint)
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_BOUND_MARKET_BATCH",
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": (
                selection.manifest_checksum if selection is not None else None
            ),
            "batch_index": selection.batch_index if selection is not None else None,
            "batch_count": selection.batch_count if selection is not None else None,
            "request_checksum": (
                selection.request.checksum if selection is not None else None
            ),
            "coverage": None,
            "failure_types": [type(exc).__name__],
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    finally:
        if database is not None:
            database.close()
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
