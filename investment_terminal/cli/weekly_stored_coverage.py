"""Privacy-safe read-only aggregate audit of stored weekly series."""

import argparse
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.operations.weekly_stored_coverage import measure_weekly_stored_coverage
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-checksum", required=True)
    parser.add_argument("--source-checkpoint-directory", required=True, type=Path)
    parser.add_argument("--weekly-checkpoint", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    if options.report_output.exists():
        raise SystemExit("Refusing to overwrite an existing coverage report")
    try:
        paths = (
            options.manifest, options.weekly_checkpoint,
            options.database, options.report_output,
        )
        if len({path.resolve() for path in paths}) != len(paths):
            raise ValueError("Input and output paths must be distinct")
        if not options.database.is_file():
            raise ValueError("Existing candle database is required")
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
        checkpoint = json.loads(options.weekly_checkpoint.read_text(encoding="utf-8"))

        def source_checkpoint(index):
            path = options.source_checkpoint_directory / f"batch_{index:04d}.json"
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

        plan = WeeklyCandleRefreshPlan.from_manifest(
            manifest, options.manifest_checksum, source_checkpoint,
            end=datetime.fromisoformat(checkpoint["end"]),
        )
        uri = options.database.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only = ON")
            payload = measure_weekly_stored_coverage(plan, checkpoint, connection)
    except Exception:
        payload = {
            "schema_version": 1,
            "operation_identity": "WEEKLY_STORED_COVERAGE",
            "status": "FAILED",
            "manifest_checksum": None,
            "selection_checksum": None,
            "end": None,
            "coverage": None,
            "weekly_failure_categories": [],
            "failure": "PRECONDITION_OR_RUNTIME_FAILURE",
            "limitations": ["failed report excludes identities, prices, paths, and exception messages"],
        }
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
