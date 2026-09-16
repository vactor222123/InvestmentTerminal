"""Evidence-bound terminal isolation for one reproduced no-price failure."""

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _verified_report,
)
from investment_terminal.operations.resumable_market_batch import (
    NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
    ResumableMarketBatchService,
    _validate_causal_failure_evidence,
)
from investment_terminal.utils.validation import validate_aware_datetime


_QUALIFICATION_IDENTITY = "MANIFEST_PARTIAL_FAILURE_QUALIFICATION"
_MISSING_PRICE_TYPES = frozenset({
    "yfinance.exceptions.YFPricesMissingError",
    "yfinance.exceptions.YFTickerMissingError",
    "yfinance.exceptions.YFTzMissingError",
})


class ManifestPartialNoPriceIsolationService:
    """Finalize one partial APIError using checksum-bound reproduced evidence."""

    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
        *,
        qualification_bytes: bytes,
        qualification_checksum: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        if not isinstance(selection, ManifestBatchSelection):
            raise TypeError("selection must be a ManifestBatchSelection")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        checksum, qualification = _verified_report(
            qualification_bytes,
            qualification_checksum,
            field_name="qualification_checksum",
        )
        outcomes = ResumableMarketBatchService._outcomes(
            checkpoint, selection.request.checksum
        )
        items = {item.symbol: item for item in selection.request.items}
        if not outcomes or not set(outcomes).issubset(items) or len(outcomes) >= len(items):
            raise ValueError("A proper partial request checkpoint is required")

        retryable = [
            symbol for symbol, outcome in outcomes.items()
            if outcome["status"] == "FAILED"
        ]
        final = [
            symbol for symbol, outcome in outcomes.items()
            if outcome["status"] == "FINAL_FAILED"
        ]
        if len(retryable) == 1 and not final:
            symbol = retryable[0]
            transitioned_count, already_final_count = 1, 0
            if outcomes[symbol].get("failure_type") != "APIError":
                raise ValueError("Checkpoint failure type is not eligible")
        elif not retryable and len(final) == 1:
            symbol = final[0]
            transitioned_count, already_final_count = 0, 1
        else:
            raise ValueError("Checkpoint must contain exactly one retryable or final failure")

        _validate_qualification(
            qualification,
            selection,
            checkpoint_outcome_count=len(outcomes),
        )
        evidence = {"partial_failure_qualification_checksum": checksum}
        final_outcome = {
            "status": "FINAL_FAILED",
            "downloaded": None,
            "inserted": None,
            "duplicates": None,
            "omitted_trailing_count": 0,
            "omission_types": [],
            "failure_type": "APIError",
            "failure_category": "NO_PRICE_DATA",
            "isolation_policy_identity": NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
            "isolation_evidence": evidence,
        }
        if already_final_count and outcomes[symbol] != final_outcome:
            raise ValueError("Existing final failure evidence does not match")
        outcomes[symbol] = final_outcome
        for outcome in outcomes.values():
            if outcome["status"] == "FAILED":
                outcome.setdefault("causal_failure_evidence", None)
        updated_checkpoint = {
            "schema_version": 4,
            "request_checksum": selection.request.checksum,
            "outcomes": outcomes,
        }
        ResumableMarketBatchService._outcomes(
            updated_checkpoint, selection.request.checksum
        )

        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        duration = (completed - started).total_seconds()
        if duration < 0:
            raise ValueError("completed_at must not be earlier than started_at")
        statuses = [outcome["status"] for outcome in outcomes.values()]
        report = {
            "schema_version": 1,
            "operation_identity": "MANIFEST_PARTIAL_NO_PRICE_ISOLATION",
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
            "isolation_policy_identity": NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
            "failure_category": "NO_PRICE_DATA",
            "evidence": evidence,
            "coverage": {
                "requested_count": len(items),
                "checkpoint_outcome_count": len(outcomes),
                "missing_count": len(items) - len(outcomes),
                "success_count": statuses.count("SUCCESS"),
                "empty_count": statuses.count("EMPTY"),
                "retryable_failure_count": statuses.count("FAILED"),
                "final_failure_count": statuses.count("FINAL_FAILED"),
                "transitioned_count": transitioned_count,
                "already_final_count": already_final_count,
            },
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, prices, paths, provider text, and exception messages",
                "terminal isolation changes only the bound checkpoint outcome and does not ingest missing request items",
            ],
        }
        return updated_checkpoint, report


def _validate_qualification(
    report: dict[str, object],
    selection: ManifestBatchSelection,
    *,
    checkpoint_outcome_count: int,
) -> None:
    expected = {
        "schema_version": 1,
        "provider_identity": "YAHOO_FINANCE",
        "qualification_identity": _QUALIFICATION_IDENTITY,
        "status": "FAILED",
        "manifest_checksum": selection.manifest_checksum,
        "batch_index": selection.batch_index,
        "batch_count": selection.batch_count,
        "request_checksum": selection.request.checksum,
        "requested_start": selection.request.start.isoformat(),
        "requested_end": selection.request.end.isoformat(),
        "coverage": None,
    }
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Qualification report binding is invalid")
    selected = report.get("selection")
    expected_selection = {
        "requested_count": len(selection.request.items),
        "checkpoint_outcome_count": checkpoint_outcome_count,
        "missing_count": len(selection.request.items) - checkpoint_outcome_count,
        "failed_candidate_count": 1,
        "selected_count": 1,
        "checkpoint_failure_types": ["APIError"],
    }
    if selected != expected_selection:
        raise ValueError("Qualification selection is invalid")
    failure = report.get("failure")
    if (
        not isinstance(failure, dict)
        or set(failure) != {"category", "exception_type_chain", "reason"}
        or failure.get("category") != "NO_PRICE_DATA"
        or failure.get("reason") != "Manifest partial-failure qualification failed"
    ):
        raise ValueError("Qualification no-price failure is invalid")
    chain = failure.get("exception_type_chain")
    _validate_causal_failure_evidence({
        "category": failure.get("category"),
        "exception_type_chain": chain,
    })
    if (
        not isinstance(chain, list)
        or not chain
        or chain[0] != "investment_terminal.utils.exceptions.APIError"
        or not any(item in _MISSING_PRICE_TYPES for item in chain)
    ):
        raise ValueError("Qualification missing-price type chain is invalid")
