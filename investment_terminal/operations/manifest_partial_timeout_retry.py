"""Evidence-bound retry of one stored timeout in a partial manifest batch."""

from collections import Counter

from investment_terminal.clients.yahoo_finance_client import (
    project_yahoo_candle_failure,
)
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepService,
)
from investment_terminal.operations.manifest_partial_causal_inventory import (
    _partial_causal_inventory_state,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _verified_report,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem,
    ResumableMarketBatchService,
    _omission_evidence,
)
from investment_terminal.utils.validation import validate_aware_datetime


_INVENTORY_IDENTITY = "MANIFEST_PARTIAL_CAUSAL_INVENTORY"
_OUTER_API_ERROR = "investment_terminal.utils.exceptions.APIError"
_TIMEOUT_TYPES = frozenset({
    "builtins.TimeoutError",
    "curl_cffi.requests.exceptions.Timeout",
})
_REDACTED_TYPES = frozenset({
    "UNRECOGNIZED_EXCEPTION_TYPE",
    "EXCEPTION_CHAIN_TRUNCATED",
})


class ManifestPartialTimeoutRetryService:
    """Retry only the unique inventory-bound timeout outcome once."""

    def __init__(self, *, importer, clock) -> None:
        self.importer = importer
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
        *,
        inventory_bytes: bytes,
        inventory_checksum: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        prepared = prepare_partial_timeout_retry(
            selection,
            checkpoint,
            inventory_bytes=inventory_bytes,
            inventory_checksum=inventory_checksum,
        )
        outcomes, before, selected, checksum = prepared
        failure = None
        try:
            result = self.importer.import_candles(
                symbol=selected.symbol,
                resolution=selection.request.resolution,
                start=selection.request.start,
                end=selection.request.end,
                currency=selected.currency,
            )
            status = "SUCCESS" if result.downloaded else "EMPTY"
            omitted, omission_types = _omission_evidence(result)
            retry_outcome = {
                "status": status,
                "downloaded": result.downloaded,
                "inserted": result.inserted,
                "duplicates": result.duplicates,
                "omitted_trailing_count": omitted,
                "omission_types": list(omission_types),
                "failure_type": None,
            }
        except Exception as exc:
            failure = project_yahoo_candle_failure(exc)
            retry_outcome = {
                "status": "FAILED",
                "downloaded": None,
                "inserted": None,
                "duplicates": None,
                "omitted_trailing_count": 0,
                "omission_types": [],
                "failure_type": type(exc).__name__,
                "causal_failure_evidence": {
                    "category": failure.category.value,
                    "exception_type_chain": list(failure.exception_type_chain),
                },
            }

        outcomes[selected.symbol] = retry_outcome
        updated_checkpoint = {
            "schema_version": 4,
            "request_checksum": selection.request.checksum,
            "outcomes": outcomes,
        }
        ResumableMarketBatchService._outcomes(
            updated_checkpoint,
            selection.request.checksum,
        )
        after = _coverage(outcomes)
        disposition = _retry_disposition(retry_outcome)
        completed = validate_aware_datetime(
            self.clock(), field_name="completed_at"
        )
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        report = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_PARTIAL_TIMEOUT_RETRY",
            "provider_identity": "YAHOO_FINANCE",
            "status": (
                "READY_FOR_SWEEP"
                if disposition != "BLOCKING"
                else "BLOCKED"
            ),
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": duration,
            "manifest_checksum": selection.manifest_checksum,
            "batch_index": selection.batch_index,
            "batch_count": selection.batch_count,
            "request_checksum": selection.request.checksum,
            "requested_start": selection.request.start.isoformat(),
            "requested_end": selection.request.end.isoformat(),
            "inventory_checksum": checksum,
            "coverage": {
                "requested_count": len(selection.request.items),
                "checkpoint_outcome_count": len(outcomes),
                "missing_count": len(selection.request.items) - len(outcomes),
                "selected_count": 1,
                "attempted_count": 1,
                "unchanged_outcome_count": len(outcomes) - 1,
                "before": before,
                "after": after,
            },
            "retry_result": {
                "status": retry_outcome["status"],
                "downloaded": retry_outcome["downloaded"],
                "inserted": retry_outcome["inserted"],
                "duplicates": retry_outcome["duplicates"],
                "omitted_trailing_count": retry_outcome[
                    "omitted_trailing_count"
                ],
                "omission_types": list(retry_outcome["omission_types"]),
                "failure_category": (
                    failure.category.value if failure is not None else None
                ),
                "exception_type_chain": (
                    list(failure.exception_type_chain)
                    if failure is not None
                    else []
                ),
                "sweep_disposition": disposition,
            },
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, exception messages, and candle values",
                "retry updates only the unique inventory-bound timeout outcome",
                "operation does not process missing members or authorize later batches, scheduling, analysis, or trading",
            ],
        }
        return updated_checkpoint, report


def prepare_partial_timeout_retry(
    selection: ManifestBatchSelection,
    checkpoint: object,
    *,
    inventory_bytes: bytes,
    inventory_checksum: str,
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, int],
    MarketBatchItem,
    str,
]:
    """Validate immutable evidence and select one private timeout item."""
    checksum, inventory = _verified_report(
        inventory_bytes,
        inventory_checksum,
        field_name="inventory_checksum",
    )
    outcomes, coverage, signatures = _partial_causal_inventory_state(
        selection,
        checkpoint,
    )
    expected = {
        "schema_version": 1,
        "operation_identity": _INVENTORY_IDENTITY,
        "provider_identity": "YAHOO_FINANCE",
        "status": "SUCCESS",
        "manifest_checksum": selection.manifest_checksum,
        "batch_index": selection.batch_index,
        "batch_count": selection.batch_count,
        "request_checksum": selection.request.checksum,
        "requested_start": selection.request.start.isoformat(),
        "requested_end": selection.request.end.isoformat(),
        "coverage": coverage,
        "causal_signatures": signatures,
        "failure": None,
    }
    if any(inventory.get(key) != value for key, value in expected.items()):
        raise ValueError("Causal inventory binding does not match checkpoint")

    timeout_signatures = [
        item
        for item in signatures
        if item["category"] == "TIMEOUT"
        and item["sweep_disposition"] == "BLOCKING"
    ]
    if coverage["blocking_failure_count"] != 1 or len(timeout_signatures) != 1:
        raise ValueError("Exactly one blocking timeout is required")
    timeout_signature = timeout_signatures[0]
    chain = timeout_signature["exception_type_chain"]
    if (
        timeout_signature["count"] != 1
        or not isinstance(chain, list)
        or not chain
        or chain[0] != _OUTER_API_ERROR
        or any(item in _REDACTED_TYPES for item in chain)
        or not any(item in _TIMEOUT_TYPES for item in chain)
    ):
        raise ValueError("Stored timeout causal evidence is not eligible")

    target_causal = {
        "category": "TIMEOUT",
        "exception_type_chain": list(chain),
    }
    candidates = [
        symbol
        for symbol, outcome in outcomes.items()
        if outcome["status"] == "FAILED"
        and outcome.get("failure_type") == "APIError"
        and outcome.get("causal_failure_evidence") == target_causal
        and not ManifestCollectionSweepService._is_deferable_outcome(outcome)
    ]
    if len(candidates) != 1:
        raise ValueError("Timeout selection is ambiguous")
    items = {item.symbol: item for item in selection.request.items}
    return outcomes, _coverage(outcomes), items[candidates[0]], checksum


def _coverage(
    outcomes: dict[str, dict[str, object]],
) -> dict[str, int]:
    statuses = Counter(item["status"] for item in outcomes.values())
    deferable = sum(
        item["status"] == "FAILED"
        and ManifestCollectionSweepService._is_deferable_outcome(item)
        for item in outcomes.values()
    )
    return {
        "success_count": statuses["SUCCESS"],
        "empty_count": statuses["EMPTY"],
        "retryable_failure_count": statuses["FAILED"],
        "final_failure_count": statuses["FINAL_FAILED"],
        "deferable_failure_count": deferable,
        "blocking_failure_count": statuses["FAILED"] - deferable,
    }


def _retry_disposition(outcome: dict[str, object]) -> str:
    if outcome["status"] != "FAILED":
        return "CLEARED"
    if ManifestCollectionSweepService._is_deferable_outcome(outcome):
        return "DEFERABLE"
    return "BLOCKING"
