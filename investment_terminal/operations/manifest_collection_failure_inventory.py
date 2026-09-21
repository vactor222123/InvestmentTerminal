"""Read-only aggregate failure inventory for a completed manifest sweep."""

from collections import Counter

from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
    ManifestCollectionSweepService,
    _validated_checkpoint_sequence,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _verified_report,
)
from investment_terminal.utils.validation import validate_aware_datetime


class ManifestCollectionFailureInventoryService:
    """Aggregate validated checkpoint failures without exposing identities."""

    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        plan: ManifestCollectionSweepPlan,
        checkpoint_reader,
        *,
        sweep_report_bytes: bytes,
        sweep_report_checksum: str,
    ) -> dict[str, object]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        checksum, sweep = _verified_report(
            sweep_report_bytes,
            sweep_report_checksum,
            field_name="sweep_report_checksum",
        )
        _, states, first_unswept = _validated_checkpoint_sequence(
            plan, checkpoint_reader
        )
        coverage = ManifestCollectionSweepService._coverage(states)
        if first_unswept != len(plan.requests) + 1:
            raise ValueError("Complete sweep checkpoint coverage is required")
        _validate_sweep_report(sweep, plan, coverage)

        outcomes = [
            outcome
            for state in states
            for outcome in state.outcomes.values()
        ]
        status_counts = Counter(item["status"] for item in outcomes)
        retryable_signatures: Counter[
            tuple[str | None, tuple[str, ...]]
        ] = Counter()
        final_signatures: Counter[tuple[str, str]] = Counter()
        blocking_count = 0
        for outcome in outcomes:
            if outcome["status"] == "FAILED":
                causal = outcome.get("causal_failure_evidence")
                category = causal["category"] if causal is not None else None
                chain = (
                    tuple(causal["exception_type_chain"])
                    if causal is not None
                    else ()
                )
                retryable_signatures[(category, chain)] += 1
                if not ManifestCollectionSweepService._is_deferable_outcome(
                    outcome
                ):
                    blocking_count += 1
            elif outcome["status"] == "FINAL_FAILED":
                final_signatures[
                    (
                        outcome["failure_category"],
                        outcome["isolation_policy_identity"],
                    )
                ] += 1
        if blocking_count:
            raise ValueError("Completed sweep contains blocking failures")

        completed = validate_aware_datetime(
            self.clock(), field_name="completed_at"
        )
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        requested_count = sum(len(request.items) for request in plan.requests)
        return {
            "schema_version": 1,
            "operation_identity": "MANIFEST_COLLECTION_FAILURE_INVENTORY",
            "provider_identity": "YAHOO_FINANCE",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": duration,
            "manifest_checksum": plan.manifest_checksum,
            "sweep_report_checksum": checksum,
            "coverage": {
                "batch_count": len(plan.requests),
                "sweep_covered_batch_count": coverage[
                    "sweep_covered_batch_count"
                ],
                "fully_complete_batch_count": coverage[
                    "fully_complete_batch_count"
                ],
                "requested_count": requested_count,
                "checkpoint_outcome_count": len(outcomes),
                "missing_count": requested_count - len(outcomes),
                "success_count": status_counts["SUCCESS"],
                "empty_count": status_counts["EMPTY"],
                "retryable_failure_count": status_counts["FAILED"],
                "final_failure_count": status_counts["FINAL_FAILED"],
                "deferable_failure_count": status_counts["FAILED"],
                "blocking_failure_count": blocking_count,
            },
            "retryable_causal_signatures": [
                {
                    "category": category,
                    "exception_type_chain": list(chain),
                    "sweep_disposition": "DEFERABLE",
                    "count": count,
                }
                for (category, chain), count in sorted(
                    retryable_signatures.items(),
                    key=lambda item: (item[0][0] or "", item[0][1]),
                )
            ],
            "final_failure_signatures": [
                {
                    "category": category,
                    "isolation_policy_identity": policy,
                    "count": count,
                }
                for (category, policy), count in sorted(final_signatures.items())
            ],
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, exception messages, and candle values",
                "legacy null causal evidence remains explicit and is never inferred",
                "inventory is read-only and does not authorize retry, terminalization, analysis, scheduling, or trading",
            ],
        }


def _validate_sweep_report(sweep, plan, coverage) -> None:
    if not isinstance(sweep, dict):
        raise ValueError("Sweep report must contain an object")
    if (
        sweep.get("schema_version") != 2
        or sweep.get("operation_identity") != "MANIFEST_COLLECTION_SWEEP"
        or sweep.get("provider_identity") != "YAHOO_FINANCE"
        or sweep.get("status") != "COMPLETE"
        or sweep.get("manifest_checksum") != plan.manifest_checksum
        or sweep.get("ending_coverage") != coverage
        or sweep.get("stop_batch_index") is not None
        or sweep.get("failure_types") != []
    ):
        raise ValueError("Completed sweep report binding is invalid")
