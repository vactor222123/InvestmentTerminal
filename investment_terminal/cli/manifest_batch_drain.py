"""CLI for a budgeted manifest-bound market-batch drain."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.operations.manifest_batch_drain import (
    ManifestBatchDrainPlan,
    ManifestBatchDrainService,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.services.historical_market_service import HistoricalMarketService
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None, writer=write_json_atomic) -> int:
    parser = argparse.ArgumentParser(description="Run a bounded market-batch drain.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-checksum", required=True)
    parser.add_argument("--checkpoint-directory", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--max-batches", type=int, required=True)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    database = None
    plan = None
    try:
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
        plan = ManifestBatchDrainPlan.from_manifest(
            manifest,
            options.manifest_checksum,
            max_batches=options.max_batches,
        )
        options.checkpoint_directory.mkdir(parents=True, exist_ok=True)

        def checkpoint_path(index):
            return options.checkpoint_directory / f"batch_{index:04d}.json"

        def read_checkpoint(index):
            path = checkpoint_path(index)
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

        database = Database(options.database)
        database.initialize()
        importer = HistoricalMarketService(
            client or YahooFinanceClient(cache_directory=options.cache_directory),
            CandleRepository(database),
        )
        payload = ManifestBatchDrainService(
            importer=importer,
            checkpoint_reader=read_checkpoint,
            checkpoint_writer=lambda index, value: writer(
                checkpoint_path(index), value
            ),
            clock=runtime_clock,
        ).run(plan)
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_BATCH_DRAIN",
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": plan.manifest_checksum if plan is not None else None,
            "budget": (
                {"max_batches": plan.max_batches} if plan is not None else None
            ),
            "starting_coverage": None,
            "current_run": None,
            "ending_coverage": None,
            "stop_batch_index": None,
            "failure_types": [type(exc).__name__],
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    finally:
        if database is not None:
            database.close()
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] in {"COMPLETE", "BUDGET_EXHAUSTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
