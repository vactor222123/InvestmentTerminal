"""CLI for a read-only completed-sweep failure inventory."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.manifest_collection_failure_inventory import (
    ManifestCollectionFailureInventoryService,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Inventory failures after a complete manifest collection sweep."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--checkpoint-directory", type=Path, required=True)
    value.add_argument("--sweep-report", type=Path, required=True)
    value.add_argument("--sweep-report-checksum", required=True)
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
    plan = None
    try:
        manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
        batch_count = len(manifest.get("batches", ()))
        plan = ManifestCollectionSweepPlan.from_manifest(
            manifest,
            options.manifest_checksum,
            max_batches=batch_count,
        )

        def read_checkpoint(index):
            path = options.checkpoint_directory / f"batch_{index:04d}.json"
            return (
                json.loads(path.read_text(encoding="utf-8"))
                if path.exists()
                else None
            )

        payload = ManifestCollectionFailureInventoryService(
            clock=runtime_clock
        ).run(
            plan,
            read_checkpoint,
            sweep_report_bytes=options.sweep_report.read_bytes(),
            sweep_report_checksum=options.sweep_report_checksum,
        )
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_COLLECTION_FAILURE_INVENTORY",
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": (
                plan.manifest_checksum if plan is not None else None
            ),
            "sweep_report_checksum": None,
            "coverage": None,
            "retryable_causal_signatures": [],
            "final_failure_signatures": [],
            "failure": {
                "type": type(exc).__name__,
                "reason": "Manifest collection failure inventory failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
