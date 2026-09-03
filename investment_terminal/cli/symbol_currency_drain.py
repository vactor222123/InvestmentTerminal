"""CLI for a budgeted complete Yahoo chart-currency drain."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_chart_metadata_client import (
    YahooChartMetadataClient,
)
from investment_terminal.operations.symbol_currency_drain import (
    SymbolCurrencyDrainService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None, writer=write_json_atomic) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--projection-checksum", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--max-total-items", type=int, required=True)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        projection = json.loads(options.projection.read_text(encoding="utf-8"))
        checkpoint = json.loads(options.checkpoint.read_text(encoding="utf-8"))
        payload = SymbolCurrencyDrainService(
            client=client or YahooChartMetadataClient(),
            checkpoint_writer=lambda value: writer(options.checkpoint, value),
            clock=runtime_clock,
        ).run(
            projection,
            options.projection_checksum,
            checkpoint,
            max_total_items=options.max_total_items,
        )
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_DRAIN",
            "provider_identity": "YAHOO_FINANCE_CHART_METADATA",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "request_checksum": None,
            "projection_checksum": None,
            "budget": None,
            "current_run": None,
            "starting_coverage": None,
            "ending_coverage": None,
            "halt_category": None,
            "failure_categories": [type(exc).__name__],
            "failure": {
                "type": type(exc).__name__,
                "reason": "Symbol currency drain failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
