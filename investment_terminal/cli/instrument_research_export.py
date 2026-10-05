"""Write one private factual instrument export and a redacted report."""

import argparse
from contextlib import closing
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from investment_terminal.operations.research_corporate_actions import (
    ResearchActionPolicy, attach_action_context,
)
from investment_terminal.operations.yahoo_corporate_actions import load_snapshot
from investment_terminal.operations.instrument_research_verification import (
    verify_instrument_research_export,
)
from investment_terminal.operations.instrument_research_export import (
    build_instrument_research_export,
)
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.utils.atomic_write import write_json_atomic


def add_action_arguments(parser):
    parser.add_argument("--schema-version", type=int, choices=(1, 2), default=1)
    parser.add_argument("--actions-snapshot", type=Path)
    parser.add_argument("--actions-sha256")
    parser.add_argument("--actions-as-of", help="Explicit UTC evidence evaluation time (schema 2)")
    parser.add_argument("--actions-maximum-age-days", type=int)


def action_arguments(options):
    """Validate explicit opt-in once; shared with the profile composition root."""
    supplied = (options.actions_snapshot, options.actions_sha256,
                options.actions_as_of, options.actions_maximum_age_days)
    if options.schema_version == 1:
        if any(value is not None for value in supplied):
            raise ValueError("Action options require schema 2")
        return []
    if options.actions_as_of is None or options.actions_maximum_age_days is None:
        raise ValueError("Schema 2 requires an explicit action freshness policy")
    ResearchActionPolicy(datetime.fromisoformat(options.actions_as_of),
                         options.actions_maximum_age_days)
    if (options.actions_snapshot is None) != (options.actions_sha256 is None):
        raise ValueError("Action snapshot and checksum must be supplied together")
    result = ["--schema-version", "2", "--actions-as-of", options.actions_as_of,
              "--actions-maximum-age-days", str(options.actions_maximum_age_days)]
    if options.actions_snapshot is not None:
        result += ["--actions-snapshot", str(options.actions_snapshot),
                   "--actions-sha256", options.actions_sha256]
    return result


def main(argv=None, *, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-checksum", required=True)
    parser.add_argument("--source-checkpoint-directory", required=True, type=Path)
    parser.add_argument("--weekly-checkpoint", required=True, type=Path)
    parser.add_argument("--projection", required=True, type=Path)
    parser.add_argument("--projection-sha256", required=True)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--history-start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    add_action_arguments(parser)
    options = parser.parse_args(argv)
    try:
        action_arguments(options)
    except (TypeError, ValueError):
        raise SystemExit("Research action options are invalid") from None
    if options.private_output.exists() or options.report_output.exists():
        raise SystemExit("Refusing to overwrite an existing export or report")
    inputs = (
        options.manifest, options.weekly_checkpoint, options.projection,
        options.database,
    )
    if options.actions_snapshot is not None:
        inputs += (options.actions_snapshot,)
    outputs = (options.private_output, options.report_output)
    if (not options.source_checkpoint_directory.is_absolute()
            or any(not path.is_absolute() for path in (*inputs, *outputs))
            or len({path.resolve() for path in (*inputs, *outputs)}) != len(inputs) + 2
            or any(path.resolve().is_relative_to(
                options.source_checkpoint_directory.resolve()
            ) for path in outputs)):
        raise SystemExit("Instrument export paths are invalid")

    try:
        snapshot = None
        action_hash = None
        if options.actions_snapshot is not None:
            snapshot, action_hash = load_snapshot(options.actions_snapshot)
            if action_hash != options.actions_sha256:
                raise ValueError("Action snapshot checksum mismatch")
        projection_bytes = options.projection.read_bytes()
        projection_sha256 = sha256(projection_bytes).hexdigest()
        if projection_sha256 != options.projection_sha256:
            raise ValueError("Private projection checksum mismatch")
        projection = json.loads(projection_bytes)
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
            private, report = build_instrument_research_export(
                plan, checkpoint, projection, projection_sha256, connection,
                symbol=options.symbol,
                history_start=datetime.fromisoformat(options.history_start),
            )
        if options.schema_version == 2:
            private, report = attach_action_context(
                private, report,
                policy=ResearchActionPolicy(
                    datetime.fromisoformat(options.actions_as_of),
                    options.actions_maximum_age_days,
                ), snapshot=snapshot, source_sha256=action_hash,
            )
            # New schema artifacts must pass the same offline consumer before write.
            verify_instrument_research_export(private, report, expected_symbol=options.symbol)
        writer(options.private_output, private)
        writer(options.report_output, report)
    except Exception:
        # Both destinations were absent at entry; remove only this invocation's files.
        try:
            options.private_output.unlink(missing_ok=True)
            options.report_output.unlink(missing_ok=True)
            failed = {
                "schema_version": options.schema_version,
                "operation_identity": "INSTRUMENT_RESEARCH_EXPORT_REPORT",
                "status": "FAILED",
                "manifest_checksum": None,
                "selection_checksum": None,
                "source_projection_sha256": None,
                "history_start": None,
                "end": None,
                "price_basis": "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT",
                "candle_count": None,
                "history_candles_sha256": None,
                "sample_count_capped_at_200": None,
                "availability": None,
                "recent_7_calendar_day_proxy": None,
                "failure": "PRECONDITION_OR_RUNTIME_FAILURE",
                "limitations": ["failed report excludes private identities and error text"],
            }
            if options.schema_version == 2:
                failed["corporate_actions"] = None
            writer(options.report_output, failed)
        except Exception:
            return 1
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
