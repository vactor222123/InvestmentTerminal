"""Read-only residual inventory after the completed-sweep no-price transition."""

from collections import Counter

from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
    _validated_checkpoint_sequence,
)
from investment_terminal.operations.manifest_completed_sweep_no_price_transition import (
    _validate_inventory_and_checkpoints,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _verified_report,
)
from investment_terminal.operations.resumable_market_batch import (
    COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
)
from investment_terminal.utils.validation import validate_aware_datetime


_OPERATION_IDENTITY = "MANIFEST_POST_TRANSITION_RESIDUAL_INVENTORY"


class ManifestPostTransitionResidualInventoryService:
    """Reconcile current checkpoint residuals without exposing identities."""

    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        plan: ManifestCollectionSweepPlan,
        checkpoint_reader,
        *,
        inventory_bytes: bytes,
        inventory_checksum: str,
        transition_report_bytes: bytes,
        transition_report_checksum: str,
    ) -> dict[str, object]:
        if not isinstance(plan, ManifestCollectionSweepPlan):
            raise TypeError("plan must be a ManifestCollectionSweepPlan")
        if not callable(checkpoint_reader):
            raise TypeError("checkpoint_reader must be callable")

        started = validate_aware_datetime(self.clock(), field_name="started_at")
        source_checksum, inventory = _verified_report(
            inventory_bytes,
            inventory_checksum,
            field_name="inventory_checksum",
        )
        transition_checksum, transition = _verified_report(
            transition_report_bytes,
            transition_report_checksum,
            field_name="transition_report_checksum",
        )
        checkpoints, states, first_unswept = _validated_checkpoint_sequence(
            plan, checkpoint_reader
        )
        if first_unswept != len(plan.requests) + 1:
            raise ValueError("Complete sweep checkpoint coverage is required")

        cohort = _validate_inventory_and_checkpoints(
            inventory,
            source_checksum,
            plan,
            checkpoints,
            states,
        )
        _validate_transition_report(
            transition,
            plan,
            source_checksum,
            eligible_count=cohort.eligible_count,
        )
        if cohort.remaining or len(cohort.already_final) != cohort.eligible_count:
            raise ValueError(
                "Current checkpoints do not match completed transition evidence"
            )

        outcomes = [
            outcome
            for state in states
            for outcome in state.outcomes.values()
        ]
        status_counts = Counter(outcome["status"] for outcome in outcomes)
        retryable_signatures: Counter[
            tuple[str | None, tuple[str, ...]]
        ] = Counter()
        final_signatures: Counter[tuple[str, str]] = Counter()
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
            elif outcome["status"] == "FINAL_FAILED":
                final_signatures[
                    (
                        outcome["failure_category"],
                        outcome["isolation_policy_identity"],
                    )
                ] += 1

        transition_final_count = len(cohort.already_final)
        final_count = status_counts["FINAL_FAILED"]
        completed = validate_aware_datetime(
            self.clock(), field_name="completed_at"
        )
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        requested_count = sum(len(request.items) for request in plan.requests)
        return {
            "schema_version": 1,
            "operation_identity": _OPERATION_IDENTITY,
            "provider_identity": "YAHOO_FINANCE",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": duration,
            "manifest_checksum": plan.manifest_checksum,
            "source_inventory_checksum": source_checksum,
            "transition_report_checksum": transition_checksum,
            "isolation_policy_identity": (
                COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
            ),
            "coverage": {
                "batch_count": len(plan.requests),
                "requested_count": requested_count,
                "checkpoint_outcome_count": len(outcomes),
                "missing_count": requested_count - len(outcomes),
                "success_count": status_counts["SUCCESS"],
                "empty_count": status_counts["EMPTY"],
                "retryable_failure_count": status_counts["FAILED"],
                "final_failure_count": final_count,
                "transition_policy_final_count": transition_final_count,
                "other_final_failure_count": final_count - transition_final_count,
            },
            "residual_causal_signatures": [
                {
                    "category": category,
                    "exception_type_chain": list(chain),
                    "source_disposition": "DEFERABLE",
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
                "report excludes symbols, currencies, prices, paths, provider text, exception messages, evidence details, and candle values",
                "legacy null causal evidence remains explicit and is never inferred",
                "inventory is read-only and does not authorize retry, terminalization, analysis, scheduling, or trading",
            ],
        }


def _validate_transition_report(
    report,
    plan,
    inventory_checksum,
    *,
    eligible_count,
) -> None:
    if not isinstance(report, dict):
        raise ValueError("Transition report must contain an object")
    if (
        report.get("schema_version") != 1
        or report.get("operation_identity")
        != "MANIFEST_COMPLETED_SWEEP_NO_PRICE_TRANSITION"
        or report.get("provider_identity") != "YAHOO_FINANCE"
        or report.get("status") != "COMPLETE"
        or report.get("manifest_checksum") != plan.manifest_checksum
        or report.get("inventory_checksum") != inventory_checksum
        or report.get("isolation_policy_identity")
        != COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
        or report.get("failure") is not None
    ):
        raise ValueError("Completed transition report binding is invalid")

    budget = report.get("budget")
    maximum = budget.get("max_checkpoints") if isinstance(budget, dict) else None
    if (
        not isinstance(budget, dict)
        or set(budget) != {"max_checkpoints"}
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or not 1 <= maximum <= len(plan.requests)
    ):
        raise ValueError("Completed transition report budget is invalid")

    starting = _coverage(
        report.get("starting_coverage"),
        {"eligible_count", "transitioned_count", "already_final_count", "remaining_count"},
    )
    current = _coverage(
        report.get("current_run"),
        {
            "processed_checkpoint_count",
            "eligible_count",
            "transitioned_count",
            "already_final_count",
            "remaining_count",
        },
    )
    ending = _coverage(
        report.get("ending_coverage"),
        {
            "eligible_count",
            "already_final_count",
            "transitioned_count",
            "final_count",
            "remaining_count",
        },
    )

    already = starting["already_final_count"]
    remaining = starting["remaining_count"]
    transitioned = current["transitioned_count"]
    processed = current["processed_checkpoint_count"]
    if (
        starting["eligible_count"] != eligible_count
        or starting["transitioned_count"] != 0
        or already + remaining != eligible_count
        or current["eligible_count"] != eligible_count
        or current["already_final_count"] != already
        or transitioned + current["remaining_count"] != remaining
        or processed > maximum
        or processed > transitioned
        or ending["eligible_count"] != eligible_count
        or ending["already_final_count"] != already
        or ending["transitioned_count"] != transitioned
        or ending["final_count"] != already + transitioned
        or ending["remaining_count"] != current["remaining_count"]
        or ending["final_count"] != eligible_count
        or ending["remaining_count"] != 0
    ):
        raise ValueError("Completed transition report coverage is invalid")


def _coverage(value, fields):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Completed transition report coverage is invalid")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in value.values()
    ):
        raise ValueError("Completed transition report coverage is invalid")
    return value
