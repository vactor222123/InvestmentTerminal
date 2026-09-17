"""Terminal isolation using causal evidence stored at failure time."""

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _verified_report,
)
from investment_terminal.operations.resumable_market_batch import (
    STORED_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY,
    ResumableMarketBatchService,
    _validate_causal_failure_evidence,
)
from investment_terminal.utils.validation import validate_aware_datetime


_DIAGNOSTIC_IDENTITY = "MANIFEST_PARTIAL_CAUSAL_EVIDENCE_DIAGNOSTIC"
_MISSING_PRICE_TYPES = frozenset({
    "yfinance.exceptions.YFPricesMissingError",
    "yfinance.exceptions.YFTickerMissingError",
    "yfinance.exceptions.YFTzMissingError",
})
_REDACTED_TYPES = frozenset({
    "UNRECOGNIZED_EXCEPTION_TYPE",
    "EXCEPTION_CHAIN_TRUNCATED",
})


class ManifestStoredNoPriceIsolationService:
    """Finalize one APIError from matching stored causal evidence."""

    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
        *,
        diagnostic_bytes: bytes,
        diagnostic_checksum: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        if not isinstance(selection, ManifestBatchSelection):
            raise TypeError("selection must be a ManifestBatchSelection")
        if not isinstance(checkpoint, dict) or checkpoint.get("schema_version") != 4:
            raise ValueError("Stored causal isolation requires checkpoint schema 4")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        checksum, diagnostic = _verified_report(
            diagnostic_bytes,
            diagnostic_checksum,
            field_name="diagnostic_checksum",
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
            source = outcomes[symbol]
            if source.get("failure_type") != "APIError":
                raise ValueError("Checkpoint failure type is not eligible")
        elif not retryable and len(final) == 1:
            symbol = final[0]
            transitioned_count, already_final_count = 0, 1
            source = None
        else:
            raise ValueError(
                "Checkpoint must contain exactly one retryable or final failure"
            )

        causal_evidence = _validate_diagnostic(
            diagnostic,
            selection,
            checkpoint_outcome_count=len(outcomes),
        )
        if source is not None and source.get("causal_failure_evidence") != causal_evidence:
            raise ValueError("Diagnostic causal evidence does not match checkpoint")

        evidence = {"causal_evidence_diagnostic_checksum": checksum}
        final_outcome = {
            "status": "FINAL_FAILED",
            "downloaded": None,
            "inserted": None,
            "duplicates": None,
            "omitted_trailing_count": 0,
            "omission_types": [],
            "failure_type": "APIError",
            "failure_category": "NO_PRICE_DATA",
            "isolation_policy_identity": (
                STORED_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
            ),
            "isolation_evidence": evidence,
        }
        if already_final_count and outcomes[symbol] != final_outcome:
            raise ValueError("Existing final failure evidence does not match")
        outcomes[symbol] = final_outcome
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
            "operation_identity": "MANIFEST_STORED_NO_PRICE_ISOLATION",
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
            "isolation_policy_identity": (
                STORED_NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY
            ),
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


def _validate_diagnostic(
    report: dict[str, object],
    selection: ManifestBatchSelection,
    *,
    checkpoint_outcome_count: int,
) -> dict[str, object]:
    expected = {
        "schema_version": 1,
        "operation_identity": _DIAGNOSTIC_IDENTITY,
        "provider_identity": "YAHOO_FINANCE",
        "status": "EVIDENCE_AVAILABLE",
        "manifest_checksum": selection.manifest_checksum,
        "batch_index": selection.batch_index,
        "batch_count": selection.batch_count,
        "request_checksum": selection.request.checksum,
        "requested_start": selection.request.start.isoformat(),
        "requested_end": selection.request.end.isoformat(),
        "failure": None,
    }
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Causal-evidence diagnostic binding is invalid")
    expected_selection = {
        "requested_count": len(selection.request.items),
        "checkpoint_outcome_count": checkpoint_outcome_count,
        "missing_count": len(selection.request.items) - checkpoint_outcome_count,
        "failed_candidate_count": 1,
        "selected_count": 1,
        "checkpoint_failure_types": ["APIError"],
    }
    if report.get("selection") != expected_selection:
        raise ValueError("Causal-evidence diagnostic selection is invalid")
    causal = report.get("causal_failure_evidence")
    _validate_causal_failure_evidence(causal)
    if not isinstance(causal, dict) or causal.get("category") != "NO_PRICE_DATA":
        raise ValueError("Stored no-price causal evidence is invalid")
    chain = causal.get("exception_type_chain")
    if (
        not isinstance(chain, list)
        or not chain
        or chain[0] != "investment_terminal.utils.exceptions.APIError"
        or any(item in _REDACTED_TYPES for item in chain)
        or not any(item in _MISSING_PRICE_TYPES for item in chain)
    ):
        raise ValueError("Stored missing-price type chain is invalid")
    return {
        "category": causal["category"],
        "exception_type_chain": list(chain),
    }
