"""CLI for bounded, resumable weekly daily-candle updates."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    WeeklyCandleRefreshService,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None, writer=write_json_atomic) -> int:
    parser = argparse.ArgumentParser(description="Refresh successful manifest series.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-checksum", required=True)
    parser.add_argument("--source-checkpoint-directory", type=Path, required=True)
    parser.add_argument("--weekly-checkpoint", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--end", type=datetime.fromisoformat, required=True)
    parser.add_argument("--max-items", type=int, required=True)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    database = None
    plan = None
    try:
        paths = [
            options.manifest, options.weekly_checkpoint, options.database,
            options.report_output,
        ]
        if len({path.resolve() for path in paths}) != len(paths):
            raise ValueError("Input and output paths must be distinct")
        source_directory = options.source_checkpoint_directory.resolve()
        if any(
            output.resolve().is_relative_to(source_directory)
            for output in (options.weekly_checkpoint, options.report_output)
        ):
            raise ValueError("Weekly outputs must not overwrite source checkpoints")
        if not options.database.is_file():
            raise ValueError("Existing candle database is required")
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))

        def read_source(index):
            path = options.source_checkpoint_directory / f"batch_{index:04d}.json"
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

        plan = WeeklyCandleRefreshPlan.from_manifest(
            manifest, options.manifest_checksum, read_source, end=options.end
        )
        checkpoint = (
            json.loads(options.weekly_checkpoint.read_text(encoding="utf-8"))
            if options.weekly_checkpoint.is_file() else None
        )
        database = Database(options.database)
        database.initialize()
        service = WeeklyCandleRefreshService(
            client=client or YahooFinanceClient(cache_directory=options.cache_directory),
            repository=CandleRepository(database),
            checkpoint_writer=lambda payload: writer(options.weekly_checkpoint, payload),
            clock=runtime_clock,
        )
        payload = service.run(plan, checkpoint, max_items=options.max_items)
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "WEEKLY_CANDLE_REFRESH",
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": plan.manifest_checksum if plan else None,
            "end": plan.end.isoformat() if plan else None,
            "selection_checksum": plan.selection_checksum if plan else None,
            "budget": {"max_items": options.max_items},
            "coverage": None,
            "failure_categories": [],
            "failure": "PRECONDITION_OR_RUNTIME_FAILURE",
            "limitations": [
                "failed report excludes identities, currencies, prices, paths, provider text, and exception messages"
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
