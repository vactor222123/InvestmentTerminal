"""CLI for private eligibility-success projection and redacted reporting."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.eligibility_success_projection import (
    EligibilitySuccessProjectionService,
)
from investment_terminal.operations.universe_eligibility_scan import EligibilityScanRequest
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, clock=None, writer=write_json_atomic) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--window-end", required=True)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        universe = json.loads(options.universe.read_text(encoding="utf-8"))
        end = datetime.fromisoformat(options.window_end.replace("Z", "+00:00"))
        if end.tzinfo is None or end.utcoffset() is None:
            raise ValueError("window-end must be timezone-aware")
        request = EligibilityScanRequest.from_universe(universe, requested_end=end)
        checkpoint = json.loads(options.checkpoint.read_text(encoding="utf-8"))
        private, payload = EligibilitySuccessProjectionService(
            clock=runtime_clock
        ).run(request, checkpoint)
        writer(options.private_output, private)
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "ELIGIBILITY_SUCCESS_PROJECTION",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "request_checksum": None,
            "universe_checksum": None,
            "projection_checksum": None,
            "coverage": None,
            "failure": {
                "type": type(exc).__name__,
                "reason": "Eligibility success projection failed",
            },
            "limitations": [
                "failed report excludes private values, paths, and exception messages"
            ],
        }
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
