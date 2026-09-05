"""Read-only aggregate diagnostic for one manifest-bound batch checkpoint."""

from datetime import datetime

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.resumable_market_batch import (
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class ManifestBatchCheckpointDiagnostic:
    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
    ) -> dict[str, object]:
        if not isinstance(selection, ManifestBatchSelection):
            raise TypeError("selection must be a ManifestBatchSelection")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        outcomes = ResumableMarketBatchService._outcomes(
            checkpoint,
            selection.request.checksum,
        )
        requested_symbols = {item.symbol for item in selection.request.items}
        if set(outcomes) != requested_symbols:
            raise ValueError("Checkpoint outcomes do not exactly cover the request")

        counts = {"SUCCESS": 0, "EMPTY": 0, "FAILED": 0}
        failure_types: set[str] = set()
        for outcome in outcomes.values():
            status = outcome.get("status")
            if status not in counts:
                raise ValueError("Checkpoint outcome status is invalid")
            counts[status] += 1
            failure_type = outcome.get("failure_type")
            if status == "FAILED":
                failure_types.add(
                    normalize_required_text(
                        failure_type,
                        field_name="failure_type",
                    )
                )
            elif failure_type is not None:
                raise ValueError("Non-failed checkpoint outcome has a failure type")

        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        return {
            "schema_version": 1,
            "operation_identity": "MANIFEST_BATCH_CHECKPOINT_DIAGNOSTIC",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": _duration_seconds(started, completed),
            "manifest_checksum": selection.manifest_checksum,
            "batch_index": selection.batch_index,
            "batch_count": selection.batch_count,
            "request_checksum": selection.request.checksum,
            "coverage": {
                "requested_count": len(selection.request.items),
                "success_count": counts["SUCCESS"],
                "empty_count": counts["EMPTY"],
                "failure_count": counts["FAILED"],
            },
            "failure_types": sorted(failure_types),
            "limitations": [
                "report excludes symbols, currencies, paths, prices, provider text, and exception messages",
                "diagnostic is read-only and does not authorize retry, later batches, analysis, or trading",
            ],
        }


def _duration_seconds(started: datetime, completed: datetime) -> float:
    duration = (completed - started).total_seconds()
    if duration < 0:
        raise ValueError("completed_at must not be earlier than started_at")
    return duration
