"""Privacy-safe raw diagnosis of one failed manifest batch series."""

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.resumable_market_batch import (
    ResumableMarketBatchService,
)
from investment_terminal.operations.single_series_candle_diagnostic import (
    _analyze_frame,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class ManifestFailedSeriesDiagnosticService:
    def __init__(self, *, client, clock) -> None:
        self.client = client
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
        items = {item.symbol: item for item in selection.request.items}
        if set(outcomes) != set(items):
            raise ValueError("Checkpoint outcomes do not exactly cover the request")

        failed_symbols = []
        checkpoint_failure_types = set()
        for symbol, outcome in outcomes.items():
            status = outcome.get("status")
            if status not in {"SUCCESS", "EMPTY", "FAILED"}:
                raise ValueError("Checkpoint outcome status is invalid")
            failure_type = outcome.get("failure_type")
            if status == "FAILED":
                failed_symbols.append(symbol)
                checkpoint_failure_types.add(
                    normalize_required_text(
                        failure_type,
                        field_name="failure_type",
                    )
                )
            elif failure_type is not None:
                raise ValueError("Non-failed checkpoint outcome has a failure type")
        if len(failed_symbols) != 1:
            raise ValueError("Checkpoint must contain exactly one failed outcome")

        selected = items[failed_symbols[0]]
        frame = self.client.get_daily_frame(
            symbol=selected.symbol,
            start=selection.request.start,
            end=selection.request.end,
        )
        coverage = _analyze_frame(frame)
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "diagnostic_identity": "MANIFEST_FAILED_SERIES_RAW_CANDLE_DIAGNOSTIC",
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
            "selection": {
                "requested_count": len(selection.request.items),
                "failed_candidate_count": 1,
                "selected_count": 1,
                "checkpoint_failure_types": sorted(checkpoint_failure_types),
            },
            "coverage": coverage,
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, names, prices, paths, provider text, and exception messages",
                "one raw series diagnostic does not mutate checkpoints, ingest candles, retry batches, or authorize later batches",
            ],
        }
