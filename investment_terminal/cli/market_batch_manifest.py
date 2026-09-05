"""CLI for offline private market-batch manifest construction."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.market_batch_manifest import MarketBatchManifestService
from investment_terminal.utils.atomic_write import write_json_atomic


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return parsed


def main(argv=None, *, clock=None, writer=write_json_atomic) -> int:
    parser = argparse.ArgumentParser(description="Build an offline market-batch manifest.")
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--projection-checksum", required=True)
    parser.add_argument("--currency-checkpoint", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--json", action="store_true")
    options = parser.parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        projection = json.loads(options.projection.read_text(encoding="utf-8"))
        checkpoint = json.loads(options.currency_checkpoint.read_text(encoding="utf-8"))
        private, payload = MarketBatchManifestService(clock=runtime_clock).run(
            projection,
            options.projection_checksum,
            checkpoint,
            resolution=options.resolution,
            start=_datetime(options.start),
            end=_datetime(options.end),
        )
        writer(options.private_output, private)
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "MARKET_BATCH_MANIFEST_CONSTRUCTION",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "projection_checksum": None,
            "currency_request_checksum": None,
            "manifest_checksum": None,
            "coverage": None,
            "failure": {
                "type": type(exc).__name__,
                "reason": "Market batch manifest construction failed",
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
