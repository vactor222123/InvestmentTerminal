"""Write private raw-close SMA values and a separate redacted report."""

import argparse
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from investment_terminal.operations.latest_raw_indicator_projection import (
    project_latest_raw_indicators,
)
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-checksum", required=True)
    parser.add_argument("--source-checkpoint-directory", required=True, type=Path)
    parser.add_argument("--weekly-checkpoint", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--end", required=True)
    parser.add_argument("--max-items", required=True, type=int)
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    options = parser.parse_args(argv)
    if options.private_output.exists() or options.report_output.exists():
        raise SystemExit("Refusing to overwrite an existing projection or report")
    inputs = (options.manifest, options.weekly_checkpoint, options.database)
    outputs = (options.private_output, options.report_output)
    if (not options.source_checkpoint_directory.is_absolute()
            or any(not path.is_absolute() for path in (*inputs, *outputs))
            or len({path.resolve() for path in (*inputs, *outputs)}) != 5
            or any(path.resolve().is_relative_to(
                options.source_checkpoint_directory.resolve()
            ) for path in outputs)):
        raise SystemExit("Private projection paths are invalid")

    try:
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
        checkpoint = json.loads(options.weekly_checkpoint.read_text(encoding="utf-8"))

        def source_checkpoint(index):
            path = options.source_checkpoint_directory / f"batch_{index:04d}.json"
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

        plan = WeeklyCandleRefreshPlan.from_manifest(
            manifest, options.manifest_checksum, source_checkpoint,
            end=datetime.fromisoformat(options.end),
        )
        uri = options.database.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            private, report = project_latest_raw_indicators(
                plan, checkpoint, connection, max_items=options.max_items,
            )
        writer(options.private_output, private)
        writer(options.report_output, report)
    except Exception:
        # Both destinations were absent at entry, so these are only this run's files.
        try:
            options.private_output.unlink(missing_ok=True)
            options.report_output.unlink(missing_ok=True)
            writer(options.report_output, {
                "schema_version": 1,
                "operation_identity": "LATEST_RAW_INDICATOR_PROJECTION_REPORT",
                "status": "FAILED",
                "manifest_checksum": None,
                "selection_checksum": None,
                "end": None,
                "price_basis": "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT",
                "selected_series_count": None,
                "processed_count": None,
                "max_items": None,
                "availability_counts": [],
                "sma50_available_count": None,
                "sma200_available_count": None,
                "recent_7_calendar_day_proxy_count": None,
                "failure": "PRECONDITION_OR_RUNTIME_FAILURE",
                "limitations": ["failed report excludes private identities and error text"],
            })
        except Exception:
            return 1
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
