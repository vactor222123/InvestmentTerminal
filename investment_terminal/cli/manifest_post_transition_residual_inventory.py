"""CLI for the read-only post-transition residual inventory."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
)
from investment_terminal.operations.manifest_post_transition_residual_inventory import (
    ManifestPostTransitionResidualInventoryService,
)
from investment_terminal.operations.resumable_market_batch import (
    COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Inventory residuals after the completed-sweep no-price transition."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--checkpoint-directory", type=Path, required=True)
    value.add_argument("--inventory", type=Path, required=True)
    value.add_argument("--inventory-checksum", required=True)
    value.add_argument("--transition-report", type=Path, required=True)
    value.add_argument("--transition-report-checksum", required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(argv: Sequence[str] | None = None, *, clock=None) -> int:
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

        payload = ManifestPostTransitionResidualInventoryService(
            clock=runtime_clock
        ).run(
            plan,
            read_checkpoint,
            inventory_bytes=options.inventory.read_bytes(),
            inventory_checksum=options.inventory_checksum,
            transition_report_bytes=options.transition_report.read_bytes(),
            transition_report_checksum=options.transition_report_checksum,
        )
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_POST_TRANSITION_RESIDUAL_INVENTORY",
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": (
                plan.manifest_checksum if plan is not None else None
            ),
            "source_inventory_checksum": None,
            "transition_report_checksum": None,
            "isolation_policy_identity": (
                COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
            ),
            "coverage": None,
            "residual_causal_signatures": [],
            "final_failure_signatures": [],
            "failure": {
                "type": type(exc).__name__,
                "reason": "Post-transition residual inventory failed",
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
