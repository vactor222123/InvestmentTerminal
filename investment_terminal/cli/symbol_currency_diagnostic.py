"""CLI for one privacy-safe invalid-currency diagnostic."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_search_client import YahooSearchClient
from investment_terminal.operations.symbol_currency_diagnostic import SymbolCurrencyDiagnosticService
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--projection-checksum", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        projection = json.loads(options.projection.read_text(encoding="utf-8"))
        checkpoint = json.loads(options.checkpoint.read_text(encoding="utf-8"))
        payload = SymbolCurrencyDiagnosticService(
            client=client or YahooSearchClient(), clock=runtime_clock
        ).run(projection, options.projection_checksum, checkpoint)
    except Exception as exc:
        now = runtime_clock()
        payload = {"schema_version": 1,
                   "operation_identity": "YAHOO_SYMBOL_CURRENCY_DIAGNOSTIC",
                   "provider_identity": "YAHOO_FINANCE_SEARCH", "status": "FAILED",
                   "started_at": now.isoformat(), "completed_at": now.isoformat(),
                   "duration_seconds": 0.0, "projection_checksum": None,
                   "qualification_request_checksum": None, "coverage": None,
                   "failure": {"type": type(exc).__name__,
                               "reason": "Yahoo symbol-currency diagnostic failed"},
                   "limitations": ["failed report excludes private values, paths, and exception messages"]}
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
