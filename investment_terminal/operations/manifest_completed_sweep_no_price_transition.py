"""Inventory-bound terminal transition for completed-sweep no-price outcomes."""

from collections import Counter
from copy import deepcopy

from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
    ManifestCollectionSweepService,
    _is_verified_no_price_evidence,
    _validated_checkpoint_sequence,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _verified_report,
)
from investment_terminal.operations.resumable_market_batch import (
    COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import validate_aware_datetime


_OPERATION_IDENTITY = "MANIFEST_COMPLETED_SWEEP_NO_PRICE_TRANSITION"


class ManifestCompletedSweepNoPriceTransitionService:
    """Finalize only inventory-bound stored no-price outcomes, checkpoint by checkpoint."""

    def __init__(self, *, checkpoint_writer, clock) -> None:
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(
        self,
        plan: ManifestCollectionSweepPlan,
        checkpoint_reader,
        *,
        inventory_bytes: bytes,
        inventory_checksum: str,
        max_checkpoints: int,
    ) -> dict[str, object]:
        if not isinstance(plan, ManifestCollectionSweepPlan):
            raise TypeError("plan must be a ManifestCollectionSweepPlan")
        if not callable(checkpoint_reader):
            raise TypeError("checkpoint_reader must be callable")
        if not callable(self.checkpoint_writer):
            raise TypeError("checkpoint_writer must be callable")
        if isinstance(max_checkpoints, bool) or not isinstance(max_checkpoints, int):
            raise TypeError("max_checkpoints must be an integer")
        if not 1 <= max_checkpoints <= len(plan.requests):
            raise ValueError(
                "max_checkpoints must be between 1 and the manifest batch count"
            )

        started = validate_aware_datetime(self.clock(), field_name="started_at")
        checksum, inventory = _verified_report(
            inventory_bytes,
            inventory_checksum,
            field_name="inventory_checksum",
        )
        checkpoints, states, first_unswept = _validated_checkpoint_sequence(
            plan, checkpoint_reader
        )
        if first_unswept != len(plan.requests) + 1:
            raise ValueError("Complete sweep checkpoint coverage is required")

        cohort = _validate_inventory_and_checkpoints(
            inventory,
            checksum,
            plan,
            checkpoints,
            states,
        )
        starting_already_final = len(cohort.already_final)
        starting_remaining = len(cohort.remaining)
        processed = transitioned = 0
        failure = None

        for index in cohort.checkpoint_indices:
            if processed >= max_checkpoints:
                break
            checkpoint = checkpoints[index - 1]
            request = plan.requests[index - 1]
            if not isinstance(checkpoint, dict) or checkpoint.get("schema_version") != 4:
                raise ValueError("Eligible no-price outcomes require checkpoint schema 4")
            outcomes = deepcopy(checkpoint["outcomes"])
            eligible_symbols = [
                symbol
                for symbol, outcome in outcomes.items()
                if _is_eligible_retryable(outcome)
            ]
            if not eligible_symbols:
                continue
            for symbol in eligible_symbols:
                outcomes[symbol] = _final_outcome(checksum)
            updated = {
                "schema_version": 4,
                "request_checksum": request.checksum,
                "outcomes": outcomes,
            }
            ResumableMarketBatchService._outcomes(updated, request.checksum)
            try:
                self.checkpoint_writer(index, updated)
            except Exception as exc:
                failure = {
                    "type": type(exc).__name__,
                    "reason": "Completed-sweep no-price checkpoint write failed",
                }
                break
            checkpoints[index - 1] = updated
            processed += 1
            transitioned += len(eligible_symbols)

        ending_remaining = starting_remaining - transitioned
        status = (
            "FAILED"
            if failure is not None
            else "COMPLETE"
            if ending_remaining == 0
            else "BUDGET_EXHAUSTED"
        )
        completed = validate_aware_datetime(
            self.clock(), field_name="completed_at"
        )
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        return {
            "schema_version": 1,
            "operation_identity": _OPERATION_IDENTITY,
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": duration,
            "manifest_checksum": plan.manifest_checksum,
            "inventory_checksum": checksum,
            "isolation_policy_identity": (
                COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
            ),
            "budget": {"max_checkpoints": max_checkpoints},
            "starting_coverage": {
                "eligible_count": cohort.eligible_count,
                "transitioned_count": 0,
                "already_final_count": starting_already_final,
                "remaining_count": starting_remaining,
            },
            "current_run": {
                "processed_checkpoint_count": processed,
                "eligible_count": cohort.eligible_count,
                "transitioned_count": transitioned,
                "already_final_count": starting_already_final,
                "remaining_count": ending_remaining,
            },
            "ending_coverage": {
                "eligible_count": cohort.eligible_count,
                "already_final_count": starting_already_final,
                "transitioned_count": transitioned,
                "final_count": starting_already_final + transitioned,
                "remaining_count": ending_remaining,
            },
            "failure": failure,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, exception messages, and candle values",
                "checkpoint files are replaced atomically one at a time and do not form one cross-file transaction",
                "transition does not contact Yahoo, access SQLite, ingest candles, analyze investments, schedule work, or authorize trading",
            ],
        }


class _Cohort:
    def __init__(self, *, eligible_count, already_final, remaining, checkpoint_indices):
        self.eligible_count = eligible_count
        self.already_final = already_final
        self.remaining = remaining
        self.checkpoint_indices = checkpoint_indices


def _validate_inventory_and_checkpoints(
    inventory,
    inventory_checksum,
    plan,
    checkpoints,
    states,
) -> _Cohort:
    coverage = inventory.get("coverage") if isinstance(inventory, dict) else None
    if (
        not isinstance(inventory, dict)
        or inventory.get("schema_version") != 1
        or inventory.get("operation_identity")
        != "MANIFEST_COLLECTION_FAILURE_INVENTORY"
        or inventory.get("provider_identity") != "YAHOO_FINANCE"
        or inventory.get("status") != "SUCCESS"
        or inventory.get("manifest_checksum") != plan.manifest_checksum
        or inventory.get("failure") is not None
        or not isinstance(coverage, dict)
    ):
        raise ValueError("Collection failure inventory binding is invalid")

    requested_count = sum(len(request.items) for request in plan.requests)
    current_outcomes = [
        outcome for state in states for outcome in state.outcomes.values()
    ]
    expected_coverage = {
        "batch_count": len(plan.requests),
        "sweep_covered_batch_count": len(plan.requests),
        "requested_count": requested_count,
        "checkpoint_outcome_count": requested_count,
        "missing_count": 0,
        "blocking_failure_count": 0,
    }
    if any(coverage.get(key) != value for key, value in expected_coverage.items()):
        raise ValueError("Collection failure inventory coverage is invalid")
    if coverage.get("deferable_failure_count") != coverage.get(
        "retryable_failure_count"
    ):
        raise ValueError("Collection failure inventory retryable coverage is invalid")

    inventory_retryable, eligible_count = _inventory_retryable_signatures(
        inventory.get("retryable_causal_signatures")
    )
    inventory_final = _inventory_final_signatures(
        inventory.get("final_failure_signatures")
    )
    if sum(inventory_retryable.values()) != coverage.get("retryable_failure_count"):
        raise ValueError("Collection failure inventory signature counts are invalid")
    if sum(inventory_final.values()) != coverage.get("final_failure_count"):
        raise ValueError("Collection failure inventory final counts are invalid")
    if eligible_count <= 0:
        raise ValueError("Collection failure inventory has no eligible no-price cohort")

    remaining = []
    already_final = []
    current_retryable = Counter()
    current_final = Counter()
    checkpoint_indices = []
    for index, checkpoint in enumerate(checkpoints, start=1):
        has_remaining = False
        if not isinstance(checkpoint, dict):
            raise ValueError("Complete checkpoint evidence is required")
        for outcome in checkpoint["outcomes"].values():
            if outcome["status"] == "FAILED":
                causal = outcome.get("causal_failure_evidence")
                key = (
                    causal.get("category") if isinstance(causal, dict) else None,
                    tuple(causal.get("exception_type_chain", ()))
                    if isinstance(causal, dict)
                    else (),
                )
                current_retryable[key] += 1
                if _is_eligible_retryable(outcome):
                    remaining.append((index, outcome))
                    has_remaining = True
            elif outcome["status"] == "FINAL_FAILED":
                if outcome.get("isolation_policy_identity") == (
                    COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
                ):
                    if outcome != _final_outcome(inventory_checksum):
                        raise ValueError(
                            "Existing completed-sweep final evidence conflicts with inventory"
                        )
                    already_final.append((index, outcome))
                else:
                    current_final[
                        (
                            outcome["failure_category"],
                            outcome["isolation_policy_identity"],
                        )
                    ] += 1
        if has_remaining:
            checkpoint_indices.append(index)

    inventory_noneligible = Counter({
        key: count
        for key, count in inventory_retryable.items()
        if not _is_verified_no_price_evidence(key[0], key[1])
    })
    current_noneligible = Counter({
        key: count
        for key, count in current_retryable.items()
        if not _is_verified_no_price_evidence(key[0], key[1])
    })
    current_eligible = sum(
        count
        for key, count in current_retryable.items()
        if _is_verified_no_price_evidence(key[0], key[1])
    )
    status_counts = Counter(outcome["status"] for outcome in current_outcomes)
    if (
        coverage.get("success_count") != status_counts["SUCCESS"]
        or coverage.get("empty_count") != status_counts["EMPTY"]
        or inventory_noneligible != current_noneligible
        or eligible_count != current_eligible + len(already_final)
        or inventory_final != current_final
    ):
        raise ValueError("Current checkpoints drift from collection failure inventory")
    return _Cohort(
        eligible_count=eligible_count,
        already_final=already_final,
        remaining=remaining,
        checkpoint_indices=checkpoint_indices,
    )


def _inventory_retryable_signatures(value):
    if not isinstance(value, list):
        raise ValueError("Collection failure inventory signatures are invalid")
    signatures = Counter()
    eligible_count = 0
    for item in value:
        if (
            not isinstance(item, dict)
            or item.get("sweep_disposition") != "DEFERABLE"
            or isinstance(item.get("count"), bool)
            or not isinstance(item.get("count"), int)
            or item["count"] <= 0
            or not isinstance(item.get("exception_type_chain"), list)
        ):
            raise ValueError("Collection failure inventory signature is invalid")
        key = (item.get("category"), tuple(item["exception_type_chain"]))
        signatures[key] += item["count"]
        if _is_verified_no_price_evidence(key[0], key[1]):
            eligible_count += item["count"]
    return signatures, eligible_count


def _inventory_final_signatures(value):
    if not isinstance(value, list):
        raise ValueError("Collection failure inventory final signatures are invalid")
    signatures = Counter()
    for item in value:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("category"), str)
            or not isinstance(item.get("isolation_policy_identity"), str)
            or isinstance(item.get("count"), bool)
            or not isinstance(item.get("count"), int)
            or item["count"] <= 0
        ):
            raise ValueError("Collection failure inventory final signature is invalid")
        signatures[(item["category"], item["isolation_policy_identity"])] += item[
            "count"
        ]
    return signatures


def _is_eligible_retryable(outcome) -> bool:
    causal = outcome.get("causal_failure_evidence")
    return (
        outcome.get("status") == "FAILED"
        and outcome.get("failure_type") == "APIError"
        and isinstance(causal, dict)
        and _is_verified_no_price_evidence(
            causal.get("category"), causal.get("exception_type_chain")
        )
    )


def _final_outcome(inventory_checksum):
    return {
        "status": "FINAL_FAILED",
        "downloaded": None,
        "inserted": None,
        "duplicates": None,
        "omitted_trailing_count": 0,
        "omission_types": [],
        "failure_type": "APIError",
        "failure_category": "NO_PRICE_DATA",
        "isolation_policy_identity": (
            COMPLETED_SWEEP_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
        ),
        "isolation_evidence": {
            "collection_failure_inventory_checksum": inventory_checksum,
        },
    }
