"""CLI for bounded, resumable weekly daily-candle updates."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    WeeklyCandleRefreshService,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.atomic_write import write_json_atomic


def _validate_output_paths(options):
    """Fail before every write if a destination can replace input evidence."""
    files = [options.manifest, options.weekly_checkpoint, options.database,
             options.report_output]
    sidecars = [Path(str(options.database.resolve()) + suffix)
                for suffix in ("-wal", "-shm", "-journal")]
    protected = files + sidecars
    for index, first in enumerate(protected):
        for second in protected[index + 1:]:
            if first.resolve() == second.resolve() or (
                first.exists() and second.exists() and first.samefile(second)
            ):
                raise ValueError("Input and output paths must be distinct")
    source = options.source_checkpoint_directory.resolve()
    cache = options.cache_directory.resolve()
    if source.is_relative_to(cache) or cache.is_relative_to(source):
        raise ValueError("Cache must be separate from source checkpoints")
    for directory in (options.source_checkpoint_directory, options.cache_directory):
        if directory.exists() and not directory.is_dir():
            raise ValueError("Directory path must not identify a file")
    for path in files:
        if path.resolve().is_relative_to(cache):
            raise ValueError("Cache must be separate from input and output files")
    for output in (options.weekly_checkpoint, options.report_output):
        if output.resolve().is_relative_to(source):
            raise ValueError("Weekly outputs must not overwrite source checkpoints")
        if output.is_symlink() or (output.exists() and not output.is_file()):
            raise ValueError("Output must be a regular file path")
    if options.report_output.exists():
        raise FileExistsError("Report destination already exists")


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
    parser.add_argument("--retry-rate-limited", action="store_true")
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    try:
        _validate_output_paths(options)
    except Exception:
        print("Unsafe weekly paths; no report written; preserve inputs", file=sys.stderr)
        return 1

    def guarded_writer(path, payload):
        _validate_output_paths(options)
        return writer(path, payload)

    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    database = None
    plan = None
    try:
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
            checkpoint_writer=lambda payload: guarded_writer(options.weekly_checkpoint, payload),
            clock=runtime_clock,
        )
        payload = service.run(
            plan, checkpoint, max_items=options.max_items,
            retry_rate_limited=options.retry_rate_limited,
        )
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 2 if options.retry_rate_limited else 1,
            "operation_identity": "WEEKLY_CANDLE_REFRESH",
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": plan.manifest_checksum if plan else None,
            "end": plan.end.isoformat() if plan else None,
            "selection_checksum": plan.selection_checksum if plan else None,
            "budget": (
                {"max_items": options.max_items, "retry_rate_limited": True}
                if options.retry_rate_limited else {"max_items": options.max_items}
            ),
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
    try:
        guarded_writer(options.report_output, payload)
    except Exception:
        print("Weekly report write failed; preserve outputs; do not rerun blindly",
              file=sys.stderr)
        return 1
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] in {"COMPLETE", "BUDGET_EXHAUSTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
