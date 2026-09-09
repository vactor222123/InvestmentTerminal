"""Read-only repaired-retrieval qualification for one failed manifest series."""

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleInvalidResponseError,
    YahooFinanceClient,
    classify_yahoo_candle_failure,
)
from investment_terminal.clients.yahoo_repaired_candle_qualification_client import (
    YahooRepairedCandleQualificationClient,
)
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_failed_series_diagnostic import (
    select_single_failed_manifest_item,
)
from investment_terminal.utils.validation import validate_aware_datetime


class ManifestRepairedSeriesQualificationService:
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
        if selection.request.resolution != "D":
            raise ValueError("Repaired-series qualification requires daily resolution")
        selected, failure_types = select_single_failed_manifest_item(
            selection, checkpoint
        )
        repaired = self.client.get_daily_frame(
            symbol=selected.symbol,
            start=selection.request.start,
            end=selection.request.end,
        )
        projection_failure_category = None
        projected_count = None
        try:
            projection = YahooFinanceClient.project_history_frame_strict(
                repaired.frame,
                symbol=selected.symbol,
                resolution=selection.request.resolution,
                currency=selected.currency,
            )
            projected_count = len(projection.candles)
            status = "QUALIFIED" if projected_count else "REJECTED"
            if not projected_count:
                projection_failure_category = "NO_PRICE_DATA"
        except YahooCandleInvalidResponseError as exc:
            status = "REJECTED"
            projection_failure_category = classify_yahoo_candle_failure(exc).value

        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        return {
            "schema_version": 2,
            "provider_identity": "YAHOO_FINANCE",
            "qualification_identity": "MANIFEST_REPAIRED_SERIES_QUALIFICATION",
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
            "selection": {
                "requested_count": len(selection.request.items),
                "failed_candidate_count": 1,
                "selected_count": 1,
                "checkpoint_failure_types": list(failure_types),
            },
            "repair": {
                "method_identity": (
                    YahooRepairedCandleQualificationClient.REPAIR_METHOD_IDENTITY
                ),
                "library_identity": "YFINANCE",
                "library_version": repaired.library_version,
                "requested": True,
                "repaired_row_count": repaired.repaired_row_count,
                "any_repaired_rows": repaired.repaired_row_count > 0,
            },
            "coverage": {
                "raw_row_count": len(repaired.frame),
                "projected_candle_count": projected_count,
                "projection_failure_category": projection_failure_category,
            },
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, exception messages, and row identities",
                "qualification is read-only and does not authorize repaired-candle persistence, checkpoint mutation, retry, or later batches",
            ],
        }
