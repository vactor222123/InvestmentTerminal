"""CLI for evidence-bound terminal isolation of one manifest series."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    ManifestTerminalSeriesIsolationService,
)
from investment_terminal.operations.resumable_market_batch import (
    FINAL_FAILURE_POLICY_IDENTITY,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Isolate one evidence-bound terminal manifest failure."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--batch-index", type=int, required=True)
    value.add_argument("--checkpoint", type=Path, required=True)
    value.add_argument("--normal-diagnostic", type=Path, required=True)
    value.add_argument("--normal-diagnostic-checksum", required=True)
    value.add_argument("--repaired-qualification", type=Path, required=True)
    value.add_argument("--repaired-qualification-checksum", required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(
    argv: Sequence[str] | None = None,
    *,
    clock=None,
    checkpoint_writer=write_json_atomic,
    report_writer=write_json_atomic,
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
        updated_checkpoint, payload = ManifestTerminalSeriesIsolationService(
            clock=runtime_clock
        ).run(
            selection,
            checkpoint,
            normal_diagnostic_bytes=options.normal_diagnostic.read_bytes(),
            normal_diagnostic_checksum=options.normal_diagnostic_checksum,
            repaired_qualification_bytes=(
                options.repaired_qualification.read_bytes()
            ),
            repaired_qualification_checksum=(
                options.repaired_qualification_checksum
            ),
        )
    except Exception:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_TERMINAL_SERIES_ISOLATION",
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
            "isolation_policy_identity": FINAL_FAILURE_POLICY_IDENTITY,
            "failure_category": None,
            "evidence": None,
            "coverage": None,
            "failure": {
                "category": "VALIDATION_OR_IO_ERROR",
                "reason": "Terminal-series isolation failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
        report_writer(options.report_output, payload)
        if options.json:
            print(json.dumps(payload, indent=2, allow_nan=False))
        return 1

    try:
        checkpoint_writer(options.checkpoint, updated_checkpoint)
    except Exception:
        now = runtime_clock()
        payload = dict(payload)
        payload.update({
            "status": "FAILED",
            "completed_at": now.isoformat(),
            "coverage": None,
            "failure": {
                "category": "CHECKPOINT_WRITE_FAILED",
                "reason": "Terminal-series checkpoint write failed",
            },
        })
        report_writer(options.report_output, payload)
        if options.json:
            print(json.dumps(payload, indent=2, allow_nan=False))
        return 1

    report_writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
