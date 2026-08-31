"""CLI for a budgeted complete universe eligibility drain."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.operations.universe_eligibility_drain import UniverseEligibilityDrainService
from investment_terminal.operations.universe_eligibility_scan import EligibilityScanRequest
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None, writer=write_json_atomic):
    parser = argparse.ArgumentParser()
    for name in ("universe", "checkpoint", "cache-directory", "report-output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--window-end", required=True)
    parser.add_argument("--max-total-items", type=int, required=True)
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
        service = UniverseEligibilityDrainService(
            client=client or YahooFinanceClient(cache_directory=options.cache_directory),
            checkpoint_writer=lambda payload: writer(options.checkpoint, payload),
            clock=runtime_clock)
        payload = service.run(request, checkpoint, max_total_items=options.max_total_items)
    except Exception as exc:
        now = runtime_clock()
        payload = {"schema_version": 1, "operation_identity": "UNIVERSE_ELIGIBILITY_DRAIN",
            "provider_identity": "YAHOO_FINANCE", "status": "FAILED",
            "started_at": now.isoformat(), "completed_at": now.isoformat(),
            "duration_seconds": 0.0, "request_checksum": None, "universe_checksum": None,
            "requested_start": None, "requested_end": None, "budget": None,
            "current_run": None, "starting_coverage": None, "ending_coverage": None,
            "halt_category": None,
            "failure": {"type": type(exc).__name__, "reason": "Universe eligibility drain failed"},
            "limitations": ["failed report excludes private values, paths, provider text, and exception messages"]}
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
