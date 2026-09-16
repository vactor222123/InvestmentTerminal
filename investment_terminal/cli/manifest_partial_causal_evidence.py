"""CLI for one read-only partial-checkpoint causal-evidence diagnostic."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_partial_causal_evidence import (
    ManifestPartialCausalEvidenceDiagnostic,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Inspect stored causal evidence for one partial manifest failure."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--batch-index", type=int, required=True)
    value.add_argument("--checkpoint", type=Path, required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(
    argv: Sequence[str] | None = None,
    *,
    clock=None,
) -> int:
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
        payload = ManifestPartialCausalEvidenceDiagnostic(
            clock=runtime_clock
        ).run(selection, checkpoint)
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_PARTIAL_CAUSAL_EVIDENCE_DIAGNOSTIC",
            "provider_identity": "YAHOO_FINANCE",
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
            "causal_failure_evidence": None,
            "failure": {
                "type": type(exc).__name__,
                "reason": "Manifest partial causal-evidence diagnostic failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] in {
        "EVIDENCE_AVAILABLE",
        "LEGACY_EVIDENCE_UNAVAILABLE",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
