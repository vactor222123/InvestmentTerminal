"""CLI for inventory-bound completed-sweep no-price terminalization."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
)
from investment_terminal.operations.manifest_completed_sweep_no_price_transition import (
    ManifestCompletedSweepNoPriceTransitionService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Finalize inventory-bound completed-sweep no-price outcomes."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--checkpoint-directory", type=Path, required=True)
    value.add_argument("--inventory", type=Path, required=True)
    value.add_argument("--inventory-checksum", required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--max-checkpoints", type=int, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(
    argv: Sequence[str] | None = None,
    *,
    clock=None,
    writer=write_json_atomic,
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

        def checkpoint_path(index):
            return options.checkpoint_directory / f"batch_{index:04d}.json"

        def read_checkpoint(index):
            path = checkpoint_path(index)
            return (
                json.loads(path.read_text(encoding="utf-8"))
                if path.exists()
                else None
            )

        payload = ManifestCompletedSweepNoPriceTransitionService(
            checkpoint_writer=lambda index, value: writer(
                checkpoint_path(index), value
            ),
            clock=runtime_clock,
        ).run(
            plan,
            read_checkpoint,
            inventory_bytes=options.inventory.read_bytes(),
            inventory_checksum=options.inventory_checksum,
            max_checkpoints=options.max_checkpoints,
        )
    except Exception as exc:
        now = runtime_clock()
        payload = {
            "schema_version": 1,
            "operation_identity": (
                "MANIFEST_COMPLETED_SWEEP_NO_PRICE_TRANSITION"
            ),
            "provider_identity": "YAHOO_FINANCE",
            "status": "FAILED",
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "duration_seconds": 0.0,
            "manifest_checksum": (
                plan.manifest_checksum if plan is not None else None
            ),
            "inventory_checksum": None,
            "isolation_policy_identity": (
                "COMPLETED_SWEEP_STORED_YAHOO_NO_PRICE_DATA_V1"
            ),
            "budget": (
                {"max_checkpoints": options.max_checkpoints}
                if isinstance(options.max_checkpoints, int)
                and not isinstance(options.max_checkpoints, bool)
                else None
            ),
            "starting_coverage": None,
            "current_run": None,
            "ending_coverage": None,
            "failure": {
                "type": type(exc).__name__,
                "reason": "Completed-sweep no-price transition failed",
            },
            "limitations": [
                "failed report excludes private values, paths, provider text, and exception messages"
            ],
        }
    writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] in {"COMPLETE", "BUDGET_EXHAUSTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
