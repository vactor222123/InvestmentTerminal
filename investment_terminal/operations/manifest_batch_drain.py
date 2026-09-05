"""Budgeted coordinator over checksum-bound market-batch requests."""

from dataclasses import dataclass

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
    ManifestBoundMarketBatchService,
    _validated_manifest_requests,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchRequest,
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import validate_aware_datetime


@dataclass(frozen=True, slots=True)
class ManifestBatchDrainPlan:
    manifest_checksum: str
    requests: tuple[MarketBatchRequest, ...]
    max_batches: int

    @classmethod
    def from_manifest(cls, value, manifest_checksum, *, max_batches: int):
        if isinstance(max_batches, bool) or not isinstance(max_batches, int):
            raise TypeError("max_batches must be an integer")
        if not 1 <= max_batches <= 25:
            raise ValueError("max_batches must be between 1 and 25")
        checksum, requests = _validated_manifest_requests(value, manifest_checksum)
        return cls(checksum, requests, max_batches)


class ManifestBatchDrainService:
    def __init__(self, *, importer, checkpoint_reader, checkpoint_writer, clock):
        self.importer = importer
        self.checkpoint_reader = checkpoint_reader
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(self, plan: ManifestBatchDrainPlan) -> dict[str, object]:
        if not isinstance(plan, ManifestBatchDrainPlan):
            raise TypeError("plan must be a ManifestBatchDrainPlan")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        checkpoints = []
        complete = []
        for index, request in enumerate(plan.requests, start=1):
            checkpoint = self.checkpoint_reader(index)
            checkpoints.append(checkpoint)
            complete.append(self._is_complete(checkpoint, request))
        first_unfinished = next(
            (index for index, done in enumerate(complete, start=1) if not done),
            len(complete) + 1,
        )
        if any(
            checkpoint is not None
            for checkpoint in checkpoints[first_unfinished:]
        ):
            raise ValueError("Manifest checkpoints contain out-of-order progress")

        starting_completed = first_unfinished - 1
        attempted_batches = attempted_items = 0
        downloaded = inserted = duplicates = 0
        failure_types = set()
        stop_batch_index = None
        status = "COMPLETE" if first_unfinished > len(plan.requests) else None
        next_index = first_unfinished

        while status is None and attempted_batches < plan.max_batches:
            request = plan.requests[next_index - 1]
            selection = ManifestBatchSelection(
                plan.manifest_checksum, next_index, len(plan.requests), request
            )
            report = ManifestBoundMarketBatchService(
                importer=self.importer,
                checkpoint_writer=lambda value, index=next_index: (
                    self.checkpoint_writer(index, value)
                ),
                clock=self.clock,
            ).run(selection, checkpoints[next_index - 1])
            current = report["coverage"]["current_run"]
            attempted_batches += 1
            attempted_items += current["attempted_count"]
            downloaded += current["downloaded_total"]
            inserted += current["inserted_total"]
            duplicates += current["duplicate_total"]
            failure_types.update(report["failure_types"])
            if report["status"] != "SUCCESS":
                status = "HALTED"
                stop_batch_index = next_index
                break
            complete[next_index - 1] = True
            next_index += 1
            if next_index > len(plan.requests):
                status = "COMPLETE"
        if status is None:
            status = "BUDGET_EXHAUSTED"

        ending_completed = next(
            (index - 1 for index, done in enumerate(complete, start=1) if not done),
            len(complete),
        )
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        return {
            "schema_version": 1,
            "operation_identity": "MANIFEST_BATCH_DRAIN",
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "manifest_checksum": plan.manifest_checksum,
            "budget": {"max_batches": plan.max_batches},
            "starting_coverage": {
                "batch_count": len(plan.requests),
                "completed_batch_count": starting_completed,
                "remaining_batch_count": len(plan.requests) - starting_completed,
            },
            "current_run": {
                "attempted_batch_count": attempted_batches,
                "attempted_item_count": attempted_items,
                "downloaded_total": downloaded,
                "inserted_total": inserted,
                "duplicate_total": duplicates,
            },
            "ending_coverage": {
                "batch_count": len(plan.requests),
                "completed_batch_count": ending_completed,
                "remaining_batch_count": len(plan.requests) - ending_completed,
            },
            "stop_batch_index": stop_batch_index,
            "failure_types": sorted(failure_types),
            "limitations": [
                "report excludes symbols, currencies, paths, prices, provider text, and exception messages",
                "a bounded drain does not authorize a larger budget, scheduling, analysis, or trading",
            ],
        }

    @staticmethod
    def _is_complete(checkpoint, request: MarketBatchRequest) -> bool:
        if checkpoint is None:
            return False
        outcomes = ResumableMarketBatchService._outcomes(
            checkpoint, request.checksum
        )
        symbols = {item.symbol for item in request.items}
        if set(outcomes) != symbols:
            return False
        return all(
            item.get("status") in {"SUCCESS", "EMPTY"}
            for item in outcomes.values()
        )
