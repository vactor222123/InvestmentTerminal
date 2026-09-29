"""Short, fail-closed composition for one bounded weekly candle slice."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from investment_terminal.cli.weekly_candle_refresh import main as refresh_main
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    _validated_outcomes,
)
from investment_terminal.utils.atomic_write import write_json_atomic
from investment_terminal.utils.validation import validate_aware_datetime


_PROFILE_FIELDS = frozenset({
    "schema_version", "operation_identity", "manifest", "manifest_checksum",
    "source_checkpoint_directory", "database", "cache_directory",
    "weekly_checkpoint_directory", "report_directory",
})
_PATH_FIELDS = _PROFILE_FIELDS - {
    "schema_version", "operation_identity", "manifest_checksum",
}


def _profile(path):
    if not path.is_absolute() or not path.is_file():
        raise ValueError("Private profile must be an existing absolute file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != _PROFILE_FIELDS:
        raise ValueError("Private profile shape is invalid")
    if (type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or value["operation_identity"] != "WEEKLY_RUN_PROFILE"):
        raise ValueError("Private profile version is invalid")
    checksum = value["manifest_checksum"]
    if (not isinstance(checksum, str)
            or re.fullmatch(r"[0-9a-f]{64}", checksum) is None):
        raise ValueError("Manifest checksum is invalid")
    paths = {}
    for field in _PATH_FIELDS:
        raw = value[field]
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("Private profile path is invalid")
        candidate = Path(raw)
        if not candidate.is_absolute():
            raise ValueError("Private profile path must be absolute")
        paths[field] = candidate.resolve()
    if (not paths["manifest"].is_file()
            or not paths["source_checkpoint_directory"].is_dir()
            or not paths["database"].is_file()):
        raise ValueError("Required private input is missing")
    source = paths["source_checkpoint_directory"]
    checkpoint_dir = paths["weekly_checkpoint_directory"]
    report_dir = paths["report_directory"]
    cache_dir = paths["cache_directory"]
    if (checkpoint_dir.is_relative_to(source)
            or report_dir.is_relative_to(source)
            or source.is_relative_to(checkpoint_dir)
            or source.is_relative_to(report_dir)
            or checkpoint_dir == report_dir
            or checkpoint_dir.is_relative_to(report_dir)
            or report_dir.is_relative_to(checkpoint_dir)):
        raise ValueError("Private output directories overlap")
    if any(cache_dir.is_relative_to(item) or item.is_relative_to(cache_dir)
           for item in (source, checkpoint_dir, report_dir)):
        raise ValueError("Cache directory overlaps private evidence")
    if (paths["manifest"].is_relative_to(checkpoint_dir)
            or paths["manifest"].is_relative_to(report_dir)
            or paths["database"].is_relative_to(checkpoint_dir)
            or paths["database"].is_relative_to(report_dir)
            or paths["manifest"].is_relative_to(cache_dir)
            or paths["database"].is_relative_to(cache_dir)
            or path.resolve().is_relative_to(checkpoint_dir)
            or path.resolve().is_relative_to(report_dir)):
        raise ValueError("Private outputs overlap required inputs")
    return value, paths


def main(argv=None, *, client=None, clock=None, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--max-items", type=int, required=True)
    parser.add_argument("--slice-id", required=True)
    parser.add_argument("--retry-rate-limited", action="store_true")
    options = parser.parse_args(argv)
    try:
        if re.fullmatch(r"[0-9]{3}", options.slice_id) is None:
            raise ValueError("slice-id must be three digits")
        value, paths = _profile(options.profile)
        end = datetime.fromisoformat(options.end)
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        source_dir = paths["source_checkpoint_directory"]

        def read_source(index):
            source_path = source_dir / f"batch_{index:04d}.json"
            return (json.loads(source_path.read_text(encoding="utf-8"))
                    if source_path.is_file() else None)

        plan = WeeklyCandleRefreshPlan.from_manifest(
            manifest, value["manifest_checksum"], read_source, end=end,
        )
        if (type(options.max_items) is not int
                or not 1 <= options.max_items <= len(plan.items)):
            raise ValueError("max-items is outside the selected series")
        now = validate_aware_datetime(
            clock() if clock is not None else datetime.now(timezone.utc),
            field_name="clock",
        )
        if end > now.astimezone(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0):
            raise ValueError("end is after the last completed UTC day")
        day = end.date().isoformat()
        checkpoint_path = (paths["weekly_checkpoint_directory"]
                           / f"weekly_candle_refresh_{day}.json")
        report_path = (paths["report_directory"]
                       / f"weekly_candle_refresh_{day}_{options.slice_id}.json")
        if report_path.exists():
            raise ValueError("Report destination already exists")
        if checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            _validated_outcomes(checkpoint, plan)

        def guarded_writer(path, payload):
            if Path(path).resolve() == report_path.resolve() and report_path.exists():
                raise FileExistsError("Report destination already exists")
            return writer(path, payload)

        refresh_args = [
            "--manifest", str(paths["manifest"]),
            "--manifest-checksum", value["manifest_checksum"],
            "--source-checkpoint-directory", str(source_dir),
            "--weekly-checkpoint", str(checkpoint_path),
            "--database", str(paths["database"]),
            "--cache-directory", str(paths["cache_directory"]),
            "--report-output", str(report_path),
            "--end", plan.end.isoformat(),
            "--max-items", str(options.max_items),
        ]
        if options.retry_rate_limited:
            refresh_args.append("--retry-rate-limited")
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = checkpoint_path.parent / "weekly_candle_refresh.lock"
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        try:
            result = refresh_main(
                refresh_args, client=client, clock=clock, writer=guarded_writer,
            )
        finally:
            lock_path.unlink()
    except Exception:
        print("Weekly run preflight or report write failed; do not rerun blindly",
              file=sys.stderr)
        return 1
    print(f"SEND: {report_path}")
    print("DO NOT SEND: private profile, manifest, checkpoints, database, cache")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
