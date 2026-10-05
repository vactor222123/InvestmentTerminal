"""Collect one bounded Yahoo action snapshot, or verify/reuse it offline."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import yfinance as yf

from investment_terminal.clients.yahoo_corporate_actions_client import YahooCorporateActionsClient
from investment_terminal.operations.yahoo_corporate_actions import (
    ActionValidationError, build_report, build_snapshot, load_snapshot,
)
from investment_terminal.operations.yahoo_price_basis_qualification import PriceBasisRequest
from investment_terminal.operations.yahoo_price_basis_provenance_report import validate_yfinance_version
from investment_terminal.utils.atomic_write import write_json_atomic
from investment_terminal.utils.validation import validate_aware_datetime


def main(argv=None, *, client=None, clock=None, writer=write_json_atomic):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", required=True, help="Inclusive YYYY-MM-DD UTC")
    parser.add_argument("--end", required=True, help="Exclusive YYYY-MM-DD UTC")
    parser.add_argument("--snapshot-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--cache-directory", type=Path)
    options = parser.parse_args(argv)
    try:
        request = PriceBasisRequest(
            options.symbol,
            datetime.strptime(options.start, "%Y-%m-%d").replace(tzinfo=timezone.utc),
            datetime.strptime(options.end, "%Y-%m-%d").replace(tzinfo=timezone.utc),
        )
        if re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=_-]{0,63}", request.symbol) is None:
            raise ValueError("Invalid symbol")
        now = validate_aware_datetime(
            clock() if clock else datetime.now(timezone.utc), field_name="clock",
        ).astimezone(timezone.utc)
        if request.end > now.replace(hour=0, minute=0, second=0, microsecond=0):
            raise ValueError("Future window")
        version = validate_yfinance_version(yf.__version__)
        snapshot_path = options.snapshot_output.resolve()
        report_path = options.report_output.resolve()
        if (snapshot_path == report_path or snapshot_path.is_relative_to(report_path)
                or report_path.is_relative_to(snapshot_path) or report_path.exists()):
            raise ValueError("Output paths overlap or report already exists")
        if options.cache_directory:
            cache = options.cache_directory.resolve()
            if any(path.is_relative_to(cache) or cache.is_relative_to(path)
                   for path in (snapshot_path, report_path)):
                raise ValueError("Cache overlaps output")
        if not snapshot_path.exists() and client is None and options.cache_directory is None:
            raise ValueError("Live retrieval requires cache directory")
        with ExitStack() as stack:
            # Protect both names against concurrent invocations of this command.
            for path in sorted((snapshot_path, report_path)):
                path.parent.mkdir(parents=True, exist_ok=True)
                lock = path.with_name(path.name + ".lock")
                with lock.open("x", encoding="ascii"):
                    pass
                stack.callback(lock.unlink)
            if report_path.exists():
                raise ValueError("Report already exists")
            persisted = snapshot_path.exists()
            reused = persisted
            snapshot = None
            file_hash = None
            category = None
            if reused:
                try:
                    snapshot, file_hash = load_snapshot(snapshot_path)
                    if (snapshot.symbol, snapshot.start, snapshot.end) != (
                            request.symbol, request.start, request.end):
                        raise ValueError("Snapshot identity mismatch")
                except Exception:
                    snapshot, file_hash = None, None
                    category = "EXISTING_SNAPSHOT_INVALID"
            else:
                try:
                    provider = client if client is not None else YahooCorporateActionsClient(
                        cache_directory=options.cache_directory,
                    )
                    frame, metadata = provider.get_action_history(
                        symbol=request.symbol, start=request.start, end=request.end,
                    )
                except Exception:
                    category = "PROVIDER_REQUEST"
                else:
                    try:
                        fetched_at = validate_aware_datetime(
                            clock() if clock else datetime.now(timezone.utc),
                            field_name="clock",
                        ).astimezone(timezone.utc)
                        snapshot = build_snapshot(
                            request, frame, metadata, fetched_at=fetched_at,
                            adapter_version=version,
                        )
                    except ActionValidationError as exc:
                        category = str(exc)
                    except Exception:
                        category = "RESPONSE_INVALID"
                if category is None:
                    try:
                        if snapshot_path.exists():
                            raise FileExistsError("Snapshot appeared during retrieval")
                        writer(snapshot_path, snapshot.to_dict())
                        stored, file_hash = load_snapshot(snapshot_path)
                        if stored != snapshot:
                            raise ValueError("Stored snapshot mismatch")
                        persisted = True
                    except Exception:
                        # A post-replace failure may leave a complete snapshot.
                        # Keep it for inspection/offline recovery, never delete it.
                        persisted = snapshot_path.exists()
                        snapshot, file_hash = None, None
                        category = "SNAPSHOT_WRITE_OR_VERIFY"
            report = build_report(
                snapshot, file_sha256=file_hash, reused=reused,
                failure_category=category, snapshot_persisted=persisted,
            )
            writer(report_path, report)
    except Exception:
        print("Action collection preflight or report write failed; preserve any snapshot",
              file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, allow_nan=False))
    return 1 if report["status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
