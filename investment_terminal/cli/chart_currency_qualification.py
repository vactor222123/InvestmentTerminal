"""CLI for one Yahoo chart-metadata currency qualification."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_chart_metadata_client import YahooChartMetadataClient
from investment_terminal.operations.chart_currency_qualification import ChartCurrencyQualificationService
from investment_terminal.utils.atomic_write import write_json_atomic


def main(argv=None, *, client=None, clock=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--projection-checksum", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        projection = json.loads(options.projection.read_text(encoding="utf-8"))
        checkpoint = json.loads(options.checkpoint.read_text(encoding="utf-8"))
        private, payload = ChartCurrencyQualificationService(
            client=client or YahooChartMetadataClient(), clock=runtime_clock
        ).run(projection, options.projection_checksum, checkpoint)
        write_json_atomic(options.private_output, private)
    except Exception as exc:
        now = runtime_clock()
        payload = {"schema_version": 1, "operation_identity": "YAHOO_CHART_CURRENCY_QUALIFICATION",
            "provider_identity": "YAHOO_FINANCE_CHART_METADATA", "status": "FAILED",
            "started_at": now.isoformat(), "completed_at": now.isoformat(), "duration_seconds": 0.0,
            "projection_checksum": None, "qualification_request_checksum": None,
            "evidence_checksum": None, "coverage": None,
            "failure": {"type": type(exc).__name__, "reason": "Yahoo chart currency qualification failed"},
            "limitations": ["failed report excludes private values, paths, and exception messages"]}
    write_json_atomic(options.report_output, payload)
    return 0 if payload["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
