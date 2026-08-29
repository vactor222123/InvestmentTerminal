"""CLI for a bounded resumable Yahoo universe eligibility scan."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.operations.universe_eligibility_scan import (
    EligibilityScanRequest,
    UniverseEligibilityScanService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run one bounded resumable Yahoo universe eligibility slice."
    )
    result.add_argument("--universe", type=Path, required=True)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--cache-directory", type=Path, required=True)
    result.add_argument("--report-output", type=Path, required=True)
    result.add_argument("--window-end", required=True)
    result.add_argument("--max-items", type=int, default=100)
    result.add_argument("--json", action="store_true")
    return result


def main(
    argv: Sequence[str] | None = None,
    *,
    client=None,
    clock=None,
    writer=write_json_atomic,
) -> int:
    options = parser().parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        universe = json.loads(options.universe.read_text(encoding="utf-8"))
        request = EligibilityScanRequest.from_universe(
            universe,
            requested_end=_datetime(options.window_end),
        )
        checkpoint = (
            json.loads(options.checkpoint.read_text(encoding="utf-8"))
            if options.checkpoint.exists()
            else None
        )
        service = UniverseEligibilityScanService(
            client=client or YahooFinanceClient(cache_directory=options.cache_directory),
            checkpoint_writer=lambda payload: writer(options.checkpoint, payload),
            clock=runtime_clock,
        )
        payload = service.run(
            request,
            checkpoint,
            max_items=options.max_items,
        )
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "universe_identity": "BROAD_US_LISTED_SECURITIES",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "request_checksum": None,
            "universe_checksum": None,
            "requested_start": None,
            "requested_end": None,
            "coverage": None,
            "failure_types": [type(exc).__name__],
            "failure": {
                "type": type(exc).__name__,
                "reason": "Universe eligibility scan failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] in {"IN_PROGRESS", "COMPLETE"} else 1


def _datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("window-end must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("window-end must be timezone-aware")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
