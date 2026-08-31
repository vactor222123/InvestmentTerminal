"""CLI for one privacy-safe Yahoo raw candle diagnostic."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_raw_candle_diagnostic_client import (
    YahooRawCandleDiagnosticClient,
)
from investment_terminal.cli.universe_eligibility_scan import _datetime
from investment_terminal.operations.single_series_candle_diagnostic import (
    SingleSeriesCandleDiagnosticService,
)
from investment_terminal.operations.universe_eligibility_scan import EligibilityScanRequest
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Diagnose one raw Yahoo series selected from an eligibility checkpoint."
    )
    result.add_argument("--universe", type=Path, required=True)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--cache-directory", type=Path, required=True)
    result.add_argument("--report-output", type=Path, required=True)
    result.add_argument("--window-end", required=True)
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
        checkpoint = json.loads(options.checkpoint.read_text(encoding="utf-8"))
        request = EligibilityScanRequest.from_universe(
            universe,
            requested_end=_datetime(options.window_end),
        )
        payload = SingleSeriesCandleDiagnosticService(
            client=client or YahooRawCandleDiagnosticClient(
                cache_directory=options.cache_directory
            ),
            clock=runtime_clock,
        ).run(request, checkpoint)
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "diagnostic_identity": "SINGLE_SERIES_RAW_CANDLE_DIAGNOSTIC",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "request_checksum": None,
            "universe_checksum": None,
            "requested_start": None,
            "requested_end": None,
            "selection": None,
            "coverage": None,
            "failure": {
                "type": type(exc).__name__,
                "reason": "Single-series raw candle diagnostic failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
