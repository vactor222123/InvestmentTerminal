"""Collect/reuse actions, export schema 2, verify locally and check SQLite."""

import argparse
from contextlib import ExitStack, closing
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
import sqlite3
import sys
from types import SimpleNamespace

from investment_terminal.cli.instrument_research_export import prepare_export
from investment_terminal.cli.instrument_research_run import main as export_main
from investment_terminal.cli.instrument_research_verify import main as verify_main, _strict_json
from investment_terminal.cli.weekly_run import _profile
from investment_terminal.cli.yahoo_corporate_actions import main as collect_main
from investment_terminal.market.corporate_actions import canonical_bytes
from investment_terminal.operations.instrument_research_verification import verify_instrument_research_export
from investment_terminal.operations.research_corporate_actions import ResearchActionPolicy, project_action_context
from investment_terminal.operations.yahoo_corporate_actions import build_report, load_snapshot


def _hash(path):
    return sha256(path.read_bytes()).hexdigest()


def _fingerprint(files, source_directory):
    sources = sorted(source_directory.glob("batch_*.json"))
    return {path: _hash(path) for path in (*files, *sources)}


def _integrity(database):
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("PRAGMA query_only = ON")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity failed")


def _available(snapshot, checksum, private, now, maximum_age_days):
    _, context = project_action_context(
        symbol=private["symbol"], currency=private["currency"],
        start=datetime.fromisoformat(private["history_start"]),
        end=datetime.fromisoformat(private["end"]),
        policy=ResearchActionPolicy(now, maximum_age_days),
        snapshot=snapshot, source_sha256=checksum,
    )
    if context["availability"] != "AVAILABLE":
        raise ValueError("Action snapshot is stale")


def main(argv=None, *, clock=None, client=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--projection", required=True, type=Path)
    parser.add_argument("--projection-sha256", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--history-start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--run-id", required=True, help="New ASCII identifier, 1..48 characters")
    parser.add_argument("--actions-maximum-age-days", required=True, type=int)
    parser.add_argument("--actions-snapshot", type=Path, help="Explicit existing snapshot for offline reuse")
    parser.add_argument("--actions-sha256", help="Required exact-file checksum for offline reuse")
    options = parser.parse_args(argv)
    current_time = clock or (lambda: datetime.now(timezone.utc))
    stage = "PREFLIGHT"
    reports = ()
    started = False
    try:
        if (re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", options.run_id) is None
                or re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=_-]{0,63}", options.symbol) is None
                or re.fullmatch(r"[0-9a-f]{64}", options.projection_sha256) is None):
            raise ValueError("Invalid request identifier or checksum")
        ResearchActionPolicy(current_time(), options.actions_maximum_age_days)
        if (options.actions_snapshot is None) != (options.actions_sha256 is None):
            raise ValueError("Offline reuse needs both snapshot and checksum")
        profile, paths = _profile(options.profile)
        if not options.projection.is_absolute() or not options.projection.is_file():
            raise ValueError("Projection must be an existing absolute file")
        projection = options.projection.resolve()
        start, end = map(datetime.fromisoformat, (options.history_start, options.end))
        # The shared projector owns UTC midnight, bounded window and future rules.
        project_action_context(symbol=options.symbol, currency=None, start=start, end=end,
                               policy=ResearchActionPolicy(current_time(), options.actions_maximum_age_days))
        checkpoint = paths["weekly_checkpoint_directory"] / f"weekly_candle_refresh_{end.date()}.json"
        stem = "research_" + options.run_id
        private_output = projection.parent / (stem + ".json")
        snapshot = (options.actions_snapshot.resolve() if options.actions_snapshot is not None
                    else projection.parent / (stem + "_actions.json"))
        report = paths["report_directory"] / (stem + ".json")
        action_report = paths["report_directory"] / (stem + "_actions.json")
        reports = (action_report, report)
        inputs = (options.profile.resolve(), projection, checkpoint,
                  paths["manifest"], paths["database"])
        outputs = (private_output, report, action_report)
        all_files = (*inputs, *outputs, snapshot)
        if (len(set(all_files)) != len(all_files)
                or any(not path.is_file() for path in inputs)
                or any(path.exists() or path.is_symlink() for path in outputs)
                or any(a != b and a.is_relative_to(b) for a in all_files for b in all_files)):
            raise ValueError("Input/output paths alias, overlap or already exist")
        private_paths = (projection, snapshot, private_output)
        forbidden = (paths["source_checkpoint_directory"], paths["weekly_checkpoint_directory"],
                     paths["report_directory"], paths["cache_directory"])
        if (any(path.is_relative_to(directory) or directory.is_relative_to(path)
                for path in private_paths for directory in forbidden)
                or any(path.is_relative_to(paths["cache_directory"]) for path in outputs)):
            raise ValueError("Private evidence must stay outside operational directories")
        reused = options.actions_snapshot is not None
        if reused:
            if (not options.actions_snapshot.is_absolute() or not snapshot.is_file()
                    or re.fullmatch(r"[0-9a-f]{64}", options.actions_sha256) is None):
                raise ValueError("Invalid reuse input")
        elif snapshot.exists() or snapshot.is_symlink():
            raise ValueError("New acquisition requires an unused snapshot path")

        bound_files = (*inputs[:-1],)  # SQLite is checked read-only, not file-hashed.
        before = _fingerprint(bound_files, paths["source_checkpoint_directory"])

        def unchanged():
            if _fingerprint(bound_files, paths["source_checkpoint_directory"]) != before:
                raise ValueError("Source evidence changed")

        with ExitStack() as locks:
            # Shared weekly lock blocks cooperating refreshes; own only acquired locks.
            for target in sorted((paths["weekly_checkpoint_directory"] / "weekly_candle_refresh.lock",
                                  private_output.with_suffix(".json.lock"), report.with_suffix(".json.lock"))):
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("x", encoding="ascii"):
                    pass
                locks.callback(target.unlink)
            prepared, redacted = prepare_export(SimpleNamespace(
                manifest=paths["manifest"], manifest_checksum=profile["manifest_checksum"],
                source_checkpoint_directory=paths["source_checkpoint_directory"],
                weekly_checkpoint=checkpoint, database=paths["database"], projection=projection,
                projection_sha256=options.projection_sha256, symbol=options.symbol,
                history_start=options.history_start, end=options.end,
            ))
            verify_instrument_research_export(prepared, redacted, expected_symbol=options.symbol)
            if reused:
                value, checksum = load_snapshot(snapshot)
                if checksum != options.actions_sha256:
                    raise ValueError("Reuse checksum mismatch")
                _available(value, checksum, prepared, current_time(), options.actions_maximum_age_days)
            unchanged()
            started = True
            stage = "ACTION_COLLECTION"
            print("1/4: Collect or reuse corporate-action evidence")
            if collect_main([
                "--symbol", options.symbol, "--start", start.date().isoformat(),
                "--end", end.date().isoformat(), "--snapshot-output", str(snapshot),
                "--report-output", str(action_report), "--cache-directory", str(paths["cache_directory"]),
            ], clock=current_time, client=client) != 0:
                raise ValueError("Collection failed")
            value, checksum = load_snapshot(snapshot)
            if reused and checksum != options.actions_sha256:
                raise ValueError("Reuse input changed")
            expected = build_report(value, file_sha256=checksum, reused=reused, snapshot_persisted=True)
            if canonical_bytes(_strict_json(action_report.read_bytes())) != canonical_bytes(expected):
                raise ValueError("Collection report mismatch")
            as_of = current_time()
            _available(value, checksum, prepared, as_of, options.actions_maximum_age_days)
            action_report_hash = _hash(action_report)
            unchanged()
            stage = "RESEARCH_EXPORT"
            print("2/4: Export schema 2 from stored candles")
            if export_main([
                "--profile", str(options.profile), "--projection", str(projection),
                "--projection-sha256", options.projection_sha256, "--symbol", options.symbol,
                "--history-start", options.history_start, "--end", options.end,
                "--private-output", str(private_output), "--report-output", str(report),
                "--schema-version", "2", "--actions-snapshot", str(snapshot),
                "--actions-sha256", checksum, "--actions-as-of", as_of.isoformat(),
                "--actions-maximum-age-days", str(options.actions_maximum_age_days),
            ]) != 0:
                raise ValueError("Export failed")
            stage = "PAIR_VERIFICATION"
            print("3/4: Verify persisted research evidence")
            report_hash, private_hash = _hash(report), _hash(private_output)
            if verify_main([
                "--private-export", str(private_output), "--report", str(report),
                "--report-sha256", report_hash, "--symbol", options.symbol,
            ]) != 0:
                raise ValueError("Pair verification failed")
            stage = "SQLITE_INTEGRITY"
            print("4/4: Read-only SQLite integrity check (may take several minutes)")
            _integrity(paths["database"])
            unchanged()
            if (_hash(snapshot) != checksum or _hash(action_report) != action_report_hash
                    or _hash(report) != report_hash or _hash(private_output) != private_hash):
                raise ValueError("Result evidence changed")
            print("SQLite integrity: ok")
        print("COMPLETE: corporate-action research run")
        print(f"ACTION_REPORT_SHA256: {action_report_hash}")
        print(f"REPORT_SHA256: {report_hash}")
    except (Exception, SystemExit):
        print(f"Research collection failed at {stage}; preserve artifacts and do not rerun blindly",
              file=sys.stderr)
        return 1
    finally:
        if started:
            for path in reports:
                if path.is_file():
                    print(f"SEND: {path}")
        print("DO NOT SEND: private snapshot, research export, profile, projection, checkpoints or database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
