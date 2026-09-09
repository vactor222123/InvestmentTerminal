"""CLI for one manifest-bound repaired-series qualification."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

import yfinance as yf

from investment_terminal.clients.yahoo_finance_client import (
    project_yahoo_candle_failure,
)
from investment_terminal.clients.yahoo_repaired_candle_qualification_client import (
    YahooRepairedCandleQualificationClient,
)
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_repaired_series_qualification import (
    ManifestRepairedSeriesQualificationService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Qualify one failed manifest series through explicit repair."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--batch-index", type=int, required=True)
    value.add_argument("--checkpoint", type=Path, required=True)
    value.add_argument("--cache-directory", type=Path, required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(argv: Sequence[str] | None = None, *, client=None, clock=None) -> int:
    options = parser().parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    selection = None
    try:
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
        selection = ManifestBatchSelection.from_manifest(
            manifest,
            options.manifest_checksum,
            options.batch_index,
        )
        checkpoint = json.loads(options.checkpoint.read_text(encoding="utf-8"))
        payload = ManifestRepairedSeriesQualificationService(
            client=client or YahooRepairedCandleQualificationClient(
                cache_directory=options.cache_directory
            ),
            clock=runtime_clock,
        ).run(selection, checkpoint)
    except Exception as exc:
        now = runtime_clock()
        failure_evidence = project_yahoo_candle_failure(exc)
        payload = {
            "schema_version": 2,
            "provider_identity": "YAHOO_FINANCE",
            "qualification_identity": "MANIFEST_REPAIRED_SERIES_QUALIFICATION",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": (
                selection.manifest_checksum if selection is not None else None
            ),
            "batch_index": selection.batch_index if selection is not None else None,
            "batch_count": selection.batch_count if selection is not None else None,
            "request_checksum": (
                selection.request.checksum if selection is not None else None
            ),
            "requested_start": (
                selection.request.start.isoformat() if selection is not None else None
            ),
            "requested_end": (
                selection.request.end.isoformat() if selection is not None else None
            ),
            "selection": None,
            "repair": {
                "method_identity": (
                    YahooRepairedCandleQualificationClient.REPAIR_METHOD_IDENTITY
                ),
                "library_identity": "YFINANCE",
                "library_version": yf.__version__,
                "requested": True,
                "repaired_row_count": None,
                "any_repaired_rows": None,
            },
            "coverage": None,
            "failure": {
                "category": failure_evidence.category.value,
                "exception_type_chain": list(
                    failure_evidence.exception_type_chain
                ),
                "reason": "Manifest repaired-series qualification failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "QUALIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
