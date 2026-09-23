"""CLI for one read-only, privacy-safe weekly candle drift diagnosis."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.operations.weekly_candle_drift_diagnostic import (
    WeeklyCandleDriftDiagnosticService,
)
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None, writer=write_json_atomic) -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose one stored weekly candle drift without mutation."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-checksum", required=True)
    parser.add_argument("--source-checkpoint-directory", type=Path, required=True)
    parser.add_argument("--weekly-checkpoint", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    if options.report_output.exists():
        raise SystemExit("Refusing to overwrite an existing diagnostic report")
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    database = None
    plan = None
    try:
        if not options.database.is_file():
            raise ValueError("Existing candle database is required")
        if len({
            path.resolve() for path in (
                options.manifest, options.weekly_checkpoint,
                options.database, options.report_output,
            )
        }) != 4:
            raise ValueError("Input and report paths must be distinct")
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
        checkpoint = json.loads(
            options.weekly_checkpoint.read_text(encoding="utf-8")
        )
        end = datetime.fromisoformat(checkpoint["end"])

        def read_source(index):
            path = options.source_checkpoint_directory / f"batch_{index:04d}.json"
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

        plan = WeeklyCandleRefreshPlan.from_manifest(
            manifest, options.manifest_checksum, read_source, end=end
        )
        database = Database(options.database)
        database.connection.execute("PRAGMA query_only = ON")
        payload = WeeklyCandleDriftDiagnosticService(
            client=client or YahooFinanceClient(cache_directory=options.cache_directory),
            repository=CandleRepository(database),
            clock=runtime_clock,
        ).run(plan, checkpoint)
    except Exception:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "WEEKLY_CANDLE_DRIFT_DIAGNOSTIC",
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": plan.manifest_checksum if plan else None,
            "end": plan.end.isoformat() if plan else None,
            "selection_checksum": plan.selection_checksum if plan else None,
            "source_drift_count": None,
            "overlap_count": None,
            "changed_overlap_count": None,
            "new_candle_count": None,
            "omitted_trailing_count": None,
            "changed_fields": [],
            "failure_category": None,
            "failure": "PRECONDITION_OR_RUNTIME_FAILURE",
            "limitations": [
                "failed report excludes identities, prices, currencies, paths, timestamps, provider text, and exception messages"
            ],
        }
    finally:
        if database is not None:
            database.close()
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] in {"REPRODUCED", "NOT_REPRODUCED", "INCONCLUSIVE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
