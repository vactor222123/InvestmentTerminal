"""Read-only aggregate causal inventory for one partial manifest checkpoint."""

from collections import Counter

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepService,
)
from investment_terminal.operations.resumable_market_batch import (
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import validate_aware_datetime


class ManifestPartialCausalInventoryDiagnostic:
    """Aggregate stored retryable causal evidence without exposing identities."""

    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
    ) -> dict[str, object]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        _, coverage, signatures = _partial_causal_inventory_state(
            selection,
            checkpoint,
        )
        completed = validate_aware_datetime(
            self.clock(), field_name="completed_at"
        )
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        return {
            "schema_version": 1,
            "operation_identity": "MANIFEST_PARTIAL_CAUSAL_INVENTORY",
            "provider_identity": "YAHOO_FINANCE",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": duration,
            "manifest_checksum": selection.manifest_checksum,
            "batch_index": selection.batch_index,
            "batch_count": selection.batch_count,
            "request_checksum": selection.request.checksum,
            "requested_start": selection.request.start.isoformat(),
            "requested_end": selection.request.end.isoformat(),
            "coverage": coverage,
            "causal_signatures": signatures,
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, exception messages, and candle values",
                "inventory does not contact a provider, mutate checkpoints, open SQLite, ingest candles, or authorize later batches",
                "legacy null evidence remains explicit and is never inferred",
            ],
        }


def _partial_causal_inventory_state(
    selection: ManifestBatchSelection,
    checkpoint: object,
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, int],
    list[dict[str, object]],
]:
    """Return validated private outcomes plus the exact redacted inventory."""
    if not isinstance(selection, ManifestBatchSelection):
        raise TypeError("selection must be a ManifestBatchSelection")
    outcomes = ResumableMarketBatchService._outcomes(
        checkpoint,
        selection.request.checksum,
    )
    requested = {item.symbol for item in selection.request.items}
    if not outcomes or not set(outcomes).issubset(requested):
        raise ValueError("Checkpoint outcomes must be a request subset")
    if len(outcomes) >= len(requested):
        raise ValueError("A proper partial checkpoint is required")

    status_counts = Counter(
        outcome["status"] for outcome in outcomes.values()
    )
    if status_counts["FAILED"] == 0:
        raise ValueError("Checkpoint has no retryable failures")
    signature_counts: Counter[
        tuple[str | None, tuple[str, ...], str]
    ] = Counter()
    for outcome in outcomes.values():
        if outcome["status"] != "FAILED":
            continue
        causal = outcome.get("causal_failure_evidence")
        if causal is None:
            category = None
            chain: tuple[str, ...] = ()
        else:
            category = causal["category"]
            chain = tuple(causal["exception_type_chain"])
        disposition = (
            "DEFERABLE"
            if ManifestCollectionSweepService._is_deferable_outcome(outcome)
            else "BLOCKING"
        )
        signature_counts[(category, chain, disposition)] += 1

    signatures = [
        {
            "category": category,
            "exception_type_chain": list(chain),
            "sweep_disposition": disposition,
            "count": count,
        }
        for (category, chain, disposition), count in sorted(
            signature_counts.items(),
            key=lambda item: (
                item[0][2],
                item[0][0] or "",
                item[0][1],
            ),
        )
    ]
    coverage = {
        "requested_count": len(requested),
        "checkpoint_outcome_count": len(outcomes),
        "missing_count": len(requested) - len(outcomes),
        "success_count": status_counts["SUCCESS"],
        "empty_count": status_counts["EMPTY"],
        "retryable_failure_count": status_counts["FAILED"],
        "final_failure_count": status_counts["FINAL_FAILED"],
        "deferable_failure_count": sum(
            item["count"]
            for item in signatures
            if item["sweep_disposition"] == "DEFERABLE"
        ),
        "blocking_failure_count": sum(
            item["count"]
            for item in signatures
            if item["sweep_disposition"] == "BLOCKING"
        ),
    }
    return outcomes, coverage, signatures
