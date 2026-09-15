"""Read-only production-path qualification of one partial manifest failure."""

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleProjection,
    project_yahoo_candle_failure,
)
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem,
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import validate_aware_datetime


QUALIFIED_FAILURE_TYPE = "APIError"


class ManifestPartialFailureQualificationService:
    """Qualify one blocking partial-checkpoint failure without mutation."""

    def __init__(self, *, client, clock) -> None:
        self.client = client
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
    ) -> dict[str, object]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        selected, selection_evidence = select_partial_api_failure(
            selection, checkpoint
        )
        try:
            projection = self.client.get_candle_projection(
                symbol=selected.symbol,
                resolution=selection.request.resolution,
                start=selection.request.start,
                end=selection.request.end,
                currency=selected.currency,
                allow_trailing_incomplete=True,
            )
            _validate_projection(projection, selection, selected)
            count = len(projection.candles)
            status = "QUALIFIED" if count else "EMPTY"
            coverage = {
                "candle_count": count,
                "omitted_trailing_count": projection.omitted_trailing_count,
                "omission_types": list(projection.omission_types),
            }
            failure = None
        except Exception as exc:
            evidence = project_yahoo_candle_failure(exc)
            status = "FAILED"
            coverage = None
            failure = {
                "category": evidence.category.value,
                "exception_type_chain": list(evidence.exception_type_chain),
                "reason": "Manifest partial-failure qualification failed",
            }
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "qualification_identity": "MANIFEST_PARTIAL_FAILURE_QUALIFICATION",
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
            "coverage": coverage,
            "failure": failure,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, exception messages, and candle values",
                "qualification does not mutate checkpoints, open SQLite, ingest candles, retry a batch, or authorize later batches",
                "a repeated request measures current behavior and cannot reconstruct the original failure cause",
            ],
        }


def select_partial_api_failure(
    selection: ManifestBatchSelection,
    checkpoint: object,
) -> tuple[MarketBatchItem, dict[str, object]]:
    """Validate a proper partial checkpoint and select its one API failure."""
    if not isinstance(selection, ManifestBatchSelection):
        raise TypeError("selection must be a ManifestBatchSelection")
    outcomes = ResumableMarketBatchService._outcomes(
        checkpoint, selection.request.checksum
    )
    items = {item.symbol: item for item in selection.request.items}
    if not outcomes or not set(outcomes).issubset(items):
        raise ValueError("Checkpoint outcomes must be a request subset")
    if len(outcomes) >= len(items):
        raise ValueError("A proper partial checkpoint is required")

    failed = [
        symbol
        for symbol, outcome in outcomes.items()
        if outcome["status"] == "FAILED"
    ]
    if len(failed) != 1:
        raise ValueError("Checkpoint must contain exactly one failed outcome")
    selected_outcome = outcomes[failed[0]]
    if selected_outcome["failure_type"] != QUALIFIED_FAILURE_TYPE:
        raise ValueError("Checkpoint failure type is not eligible")
    return items[failed[0]], {
        "requested_count": len(items),
        "checkpoint_outcome_count": len(outcomes),
        "missing_count": len(items) - len(outcomes),
        "failed_candidate_count": 1,
        "selected_count": 1,
        "checkpoint_failure_types": [QUALIFIED_FAILURE_TYPE],
    }


def _validate_projection(
    projection: object,
    selection: ManifestBatchSelection,
    selected: MarketBatchItem,
) -> None:
    if not isinstance(projection, YahooCandleProjection):
        raise ValueError("Yahoo candle projection is invalid")
    if not projection.candles and projection.omitted_trailing_count:
        raise ValueError("Empty projection cannot contain omission evidence")
    previous = None
    for candle in projection.candles:
        timestamp = validate_aware_datetime(
            candle.timestamp, field_name="candle timestamp"
        )
        if (
            candle.symbol != selected.symbol
            or candle.resolution != selection.request.resolution
            or candle.currency != selected.currency
            or not selection.request.start <= timestamp < selection.request.end
            or (previous is not None and timestamp <= previous)
        ):
            raise ValueError("Yahoo candle projection does not match request")
        previous = timestamp
