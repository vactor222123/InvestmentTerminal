"""CLI for terminal isolation using stored no-price causal evidence."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_stored_no_price_isolation import (
    ManifestStoredNoPriceIsolationService,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _reject_constant,
    _unique_object,
)
from investment_terminal.operations.resumable_market_batch import (
    STORED_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Isolate one checksum-bound stored no-price failure."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--batch-index", type=int, required=True)
    value.add_argument("--checkpoint", type=Path, required=True)
    value.add_argument("--diagnostic", type=Path, required=True)
    value.add_argument("--diagnostic-checksum", required=True)
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
        manifest = _strict_json_file(options.manifest)
        selection = ManifestBatchSelection.from_manifest(
            manifest, options.manifest_checksum, options.batch_index
        )
        checkpoint = _strict_json_file(options.checkpoint)
        updated, payload = ManifestStoredNoPriceIsolationService(
            clock=runtime_clock
        ).run(
            selection,
            checkpoint,
            diagnostic_bytes=options.diagnostic.read_bytes(),
            diagnostic_checksum=options.diagnostic_checksum,
        )
    except Exception:
        payload = _failed_payload(
            selection, runtime_clock(), "VALIDATION_OR_IO_ERROR"
        )
        report_writer(options.report_output, payload)
        if options.json:
            print(json.dumps(payload, indent=2, allow_nan=False))
        return 1
    try:
        checkpoint_writer(options.checkpoint, updated)
    except Exception:
        payload = _failed_payload(
            selection, runtime_clock(), "CHECKPOINT_WRITE_FAILED"
        )
        report_writer(options.report_output, payload)
        if options.json:
            print(json.dumps(payload, indent=2, allow_nan=False))
        return 1
    report_writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0


def _strict_json_file(path: Path) -> object:
    try:
        return json.loads(
            path.read_bytes().decode("utf-8"),
            parse_constant=lambda value: _reject_constant(value),
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Input must contain strict UTF-8 JSON") from exc


def _failed_payload(
    selection: ManifestBatchSelection | None,
    now: datetime,
    category: str,
) -> dict[str, object]:
    bound = selection is not None
    return {
        "schema_version": 1,
        "operation_identity": "MANIFEST_STORED_NO_PRICE_ISOLATION",
        "status": "FAILED",
        "started_at": now.isoformat(),
        "completed_at": now.isoformat(),
        "duration_seconds": 0.0,
        "manifest_checksum": selection.manifest_checksum if bound else None,
        "batch_index": selection.batch_index if bound else None,
        "batch_count": selection.batch_count if bound else None,
        "request_checksum": selection.request.checksum if bound else None,
        "requested_start": selection.request.start.isoformat() if bound else None,
        "requested_end": selection.request.end.isoformat() if bound else None,
        "isolation_policy_identity": (
            STORED_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
        ),
        "failure_category": None,
        "evidence": None,
        "coverage": None,
        "failure": {
            "category": category,
            "reason": "Stored no-price isolation failed",
        },
        "limitations": [
            "failed report excludes private values, paths, provider text, and exception messages"
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
