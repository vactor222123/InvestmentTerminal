"""Read-only diagnostic for causal evidence in one partial checkpoint."""

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_partial_failure_qualification import (
    select_partial_api_failure,
)
from investment_terminal.operations.resumable_market_batch import (
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import validate_aware_datetime


class ManifestPartialCausalEvidenceDiagnostic:
    """Project one stored partial API failure without provider access."""

    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
    ) -> dict[str, object]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        _, selection_evidence = select_partial_api_failure(selection, checkpoint)
        outcomes = ResumableMarketBatchService._outcomes(
            checkpoint,
            selection.request.checksum,
        )
        failed_outcome = next(
            outcome for outcome in outcomes.values() if outcome["status"] == "FAILED"
        )
        stored_evidence = failed_outcome.get("causal_failure_evidence")
        causal_evidence = (
            None
            if stored_evidence is None
            else {
                "category": stored_evidence["category"],
                "exception_type_chain": list(
                    stored_evidence["exception_type_chain"]
                ),
            }
        )
        status = (
            "EVIDENCE_AVAILABLE"
            if causal_evidence is not None
            else "LEGACY_EVIDENCE_UNAVAILABLE"
        )
        completed = validate_aware_datetime(
            self.clock(), field_name="completed_at"
        )
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        return {
            "schema_version": 1,
            "operation_identity": "MANIFEST_PARTIAL_CAUSAL_EVIDENCE_DIAGNOSTIC",
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": duration,
            "manifest_checksum": selection.manifest_checksum,
            "batch_index": selection.batch_index,
            "batch_count": selection.batch_count,
            "request_checksum": selection.request.checksum,
            "requested_start": selection.request.start.isoformat(),
            "requested_end": selection.request.end.isoformat(),
            "selection": selection_evidence,
            "causal_failure_evidence": causal_evidence,
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, and exception messages",
                "diagnostic does not contact a provider, mutate checkpoints, open SQLite, ingest candles, or authorize later batches",
                "legacy null evidence is reported as unavailable and is never inferred",
            ],
        }
