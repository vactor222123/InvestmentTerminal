"""CLI for resumable private Yahoo symbol-currency qualification."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_chart_metadata_client import YahooChartMetadataClient
from investment_terminal.operations.symbol_currency_qualification import SymbolCurrencyQualificationService
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--projection-checksum", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        projection = json.loads(options.projection.read_text(encoding="utf-8"))
        checkpoint = json.loads(options.checkpoint.read_text(encoding="utf-8")) if options.checkpoint.exists() else None
        payload = SymbolCurrencyQualificationService(
            client=client or YahooChartMetadataClient(),
            checkpoint_writer=lambda value: write_json_atomic(options.checkpoint, value),
            clock=runtime_clock,
        ).run(projection, options.projection_checksum, checkpoint, max_items=options.max_items)
    except Exception as exc:
        now = runtime_clock()
        payload = {"schema_version": 2, "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
                   "provider_identity": "YAHOO_FINANCE_CHART_METADATA", "status": "FAILED",
                   "started_at": now.isoformat(), "completed_at": now.isoformat(),
                   "duration_seconds": 0.0, "request_checksum": None,
                   "projection_checksum": None, "coverage": None,
                   "halt_category": None, "failure_categories": [type(exc).__name__],
                   "limitations": ["failed report excludes private values, paths, and exception messages"]}
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] in {"IN_PROGRESS", "COMPLETE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
