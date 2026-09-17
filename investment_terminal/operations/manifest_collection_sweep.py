"""Bounded manifest collection that defers only local candle defects."""

from dataclasses import dataclass

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    YahooCandleInvalidResponseError,
    project_yahoo_candle_failure,
)
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
    ManifestBoundMarketBatchService,
    _validated_manifest_requests,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchRequest,
    ResumableMarketBatchService,
)
from investment_terminal.utils.exceptions import APIError
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


DEFERRED_FAILURE_TYPE = "YahooCandleInvalidResponseError"
DEFERRED_NO_PRICE_FAILURE_TYPE = "APIError"
_MISSING_PRICE_TYPES = frozenset({
    "yfinance.exceptions.YFPricesMissingError",
    "yfinance.exceptions.YFTickerMissingError",
    "yfinance.exceptions.YFTzMissingError",
})
_REDACTED_TYPES = frozenset({
    "UNRECOGNIZED_EXCEPTION_TYPE",
    "EXCEPTION_CHAIN_TRUNCATED",
})


@dataclass(frozen=True, slots=True)
class ManifestCollectionSweepPlan:
    manifest_checksum: str
    requests: tuple[MarketBatchRequest, ...]
    max_batches: int

    @classmethod
    def from_manifest(cls, value, manifest_checksum, *, max_batches: int):
        checksum, requests = _validated_manifest_requests(value, manifest_checksum)
        if isinstance(max_batches, bool) or not isinstance(max_batches, int):
            raise TypeError("max_batches must be an integer")
        if not 1 <= max_batches <= len(requests):
            raise ValueError(
                "max_batches must be between 1 and the manifest batch count"
            )
        return cls(checksum, requests, max_batches)


@dataclass(frozen=True, slots=True)
class _CheckpointState:
    outcomes: dict[str, dict[str, object]]
    covered: bool
    complete: bool
    deferred_failure_count: int
    deferred_failure_types: frozenset[str]
    blocking_failure_types: frozenset[str]


def validate_manifest_collection_checkpoints(plan, checkpoint_reader) -> None:
    """Validate the complete checkpoint sequence before runtime composition."""
    _validated_checkpoint_sequence(plan, checkpoint_reader)


class ManifestCollectionSweepService:
    """Collect unattempted requests while preserving deferred local defects."""

    def __init__(self, *, importer, checkpoint_reader, checkpoint_writer, clock):
        self.importer = importer
        self.checkpoint_reader = checkpoint_reader
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(self, plan: ManifestCollectionSweepPlan) -> dict[str, object]:
        if not isinstance(plan, ManifestCollectionSweepPlan):
            raise TypeError("plan must be a ManifestCollectionSweepPlan")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        checkpoints, states, first_unswept = _validated_checkpoint_sequence(
            plan, self.checkpoint_reader
        )

        starting = self._coverage(states)
        attempted_batches = attempted_items = 0
        downloaded = inserted = duplicates = omitted = 0
        omission_types: set[str] = set()
        deferred_current = 0
        failure_types: set[str] = set()
        stop_batch_index = None
        next_index = first_unswept
        status = "COMPLETE" if first_unswept > len(plan.requests) else None

        while status is None and attempted_batches < plan.max_batches:
            request = plan.requests[next_index - 1]
            before = states[next_index - 1]
            if before.blocking_failure_types:
                status = "HALTED"
                stop_batch_index = next_index
                failure_types.update(before.blocking_failure_types)
                break

            latest_checkpoint = checkpoints[next_index - 1]
            write_count = 0

            def write(value, *, index=next_index):
                nonlocal latest_checkpoint, write_count
                self.checkpoint_writer(index, value)
                latest_checkpoint = value
                checkpoints[index - 1] = value
                write_count += 1

            selection = ManifestBatchSelection(
                plan.manifest_checksum,
                next_index,
                len(plan.requests),
                request,
            )
            attempted_batches += 1
            halted_error = None
            try:
                ManifestBoundMarketBatchService(
                    importer=self.importer,
                    checkpoint_writer=write,
                    clock=self.clock,
                ).run(
                    selection,
                    latest_checkpoint,
                    retry_failed=False,
                    continue_after_failure=self._is_deferable_failure,
                )
            except Exception as exc:
                if write_count == 0:
                    raise
                halted_error = exc

            after = self._checkpoint_state(latest_checkpoint, request)
            states[next_index - 1] = after
            new_outcomes = [
                outcome
                for symbol, outcome in after.outcomes.items()
                if symbol not in before.outcomes
            ]
            attempted_items += len(new_outcomes)
            downloaded += sum(item["downloaded"] or 0 for item in new_outcomes)
            inserted += sum(item["inserted"] or 0 for item in new_outcomes)
            duplicates += sum(item["duplicates"] or 0 for item in new_outcomes)
            omitted += sum(
                item["omitted_trailing_count"] for item in new_outcomes
            )
            omission_types.update(
                omission_type
                for item in new_outcomes
                for omission_type in item["omission_types"]
            )
            deferred_current += sum(
                self._is_deferable_outcome(item)
                for item in new_outcomes
            )

            if halted_error is not None:
                status = "HALTED"
                stop_batch_index = next_index
                failure_types.add(type(halted_error).__name__)
                break
            if not after.covered:
                raise RuntimeError("Collection sweep batch did not reach coverage")

            next_index += 1
            if next_index > len(plan.requests):
                status = "COMPLETE"

        if status is None:
            status = "BUDGET_EXHAUSTED"

        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        return {
            "schema_version": 2,
            "operation_identity": "MANIFEST_COLLECTION_SWEEP",
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "manifest_checksum": plan.manifest_checksum,
            "budget": {"max_batches": plan.max_batches},
            "starting_coverage": starting,
            "current_run": {
                "attempted_batch_count": attempted_batches,
                "attempted_item_count": attempted_items,
                "downloaded_total": downloaded,
                "inserted_total": inserted,
                "duplicate_total": duplicates,
                "omitted_trailing_total": omitted,
                "omission_types": sorted(omission_types),
                "deferred_failure_count": deferred_current,
            },
            "ending_coverage": self._coverage(states),
            "stop_batch_index": stop_batch_index,
            "failure_types": sorted(failure_types),
            "limitations": [
                "report excludes symbols, currencies, paths, prices, provider text, and exception messages",
                "sweep completion means attempted coverage and may retain deferred failures",
                "collection does not authorize remediation, scheduling, analysis, or trading",
            ],
        }

    @staticmethod
    def _is_deferable_failure(error: BaseException) -> bool:
        if type(error) is YahooCandleInvalidResponseError:
            return True
        if type(error) is not APIError:
            return False
        evidence = project_yahoo_candle_failure(error)
        return _is_verified_no_price_evidence(
            evidence.category.value,
            evidence.exception_type_chain,
        )

    @staticmethod
    def _is_deferable_outcome(outcome: dict[str, object]) -> bool:
        if outcome.get("status") != "FAILED":
            return False
        failure_type = outcome.get("failure_type")
        if failure_type == DEFERRED_FAILURE_TYPE:
            return True
        causal = outcome.get("causal_failure_evidence")
        if failure_type != DEFERRED_NO_PRICE_FAILURE_TYPE or not isinstance(
            causal, dict
        ):
            return False
        return _is_verified_no_price_evidence(
            causal.get("category"),
            causal.get("exception_type_chain"),
        )

    @staticmethod
    def _checkpoint_state(
        checkpoint: object | None,
        request: MarketBatchRequest,
    ) -> _CheckpointState:
        outcomes = ResumableMarketBatchService._outcomes(
            checkpoint, request.checksum
        )
        requested = {item.symbol for item in request.items}
        if not set(outcomes).issubset(requested):
            raise ValueError("Checkpoint outcomes are outside the request")

        blocking_failure_types: set[str] = set()
        deferred_failure_types: set[str] = set()
        deferred = 0
        for outcome in outcomes.values():
            failure_type = outcome.get("failure_type")
            if outcome["status"] == "FAILED":
                normalized = normalize_required_text(
                    failure_type, field_name="failure_type"
                )
                if ManifestCollectionSweepService._is_deferable_outcome(outcome):
                    deferred += 1
                    deferred_failure_types.add(normalized)
                else:
                    blocking_failure_types.add(normalized)
            elif outcome["status"] != "FINAL_FAILED" and failure_type is not None:
                raise ValueError("Non-failed checkpoint outcome has a failure type")

        exact = set(outcomes) == requested
        covered = exact and not blocking_failure_types
        complete = exact and all(
            outcome["status"] != "FAILED" for outcome in outcomes.values()
        )
        return _CheckpointState(
            outcomes,
            covered,
            complete,
            deferred,
            frozenset(deferred_failure_types),
            frozenset(blocking_failure_types),
        )

    @staticmethod
    def _coverage(states: list[_CheckpointState]) -> dict[str, object]:
        covered_states = [state for state in states if state.covered]
        return {
            "batch_count": len(states),
            "sweep_covered_batch_count": len(covered_states),
            "fully_complete_batch_count": sum(
                state.complete for state in covered_states
            ),
            "remaining_unswept_batch_count": len(states) - len(covered_states),
            "deferred_failure_count": sum(
                state.deferred_failure_count for state in covered_states
            ),
            "deferred_failure_types": (
                sorted({
                    failure_type
                    for state in covered_states
                    for failure_type in state.deferred_failure_types
                })
            ),
        }


def _is_verified_no_price_evidence(category: object, chain: object) -> bool:
    return (
        category == YahooCandleFailureCategory.NO_PRICE_DATA.value
        and isinstance(chain, (list, tuple))
        and bool(chain)
        and chain[0] == "investment_terminal.utils.exceptions.APIError"
        and not any(item in _REDACTED_TYPES for item in chain)
        and any(item in _MISSING_PRICE_TYPES for item in chain)
    )


def _validated_checkpoint_sequence(plan, checkpoint_reader):
    if not isinstance(plan, ManifestCollectionSweepPlan):
        raise TypeError("plan must be a ManifestCollectionSweepPlan")
    if not callable(checkpoint_reader):
        raise TypeError("checkpoint_reader must be callable")
    checkpoints = [
        checkpoint_reader(index) for index in range(1, len(plan.requests) + 1)
    ]
    states = [
        ManifestCollectionSweepService._checkpoint_state(checkpoint, request)
        for checkpoint, request in zip(checkpoints, plan.requests, strict=True)
    ]
    first_unswept = next(
        (
            index
            for index, state in enumerate(states, start=1)
            if not state.covered
        ),
        len(states) + 1,
    )
    if any(checkpoint is not None for checkpoint in checkpoints[first_unswept:]):
        raise ValueError("Manifest checkpoints contain out-of-order sweep progress")
    return checkpoints, states, first_unswept
