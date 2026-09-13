"""Evidence-bound terminal isolation for one failed manifest series."""

from datetime import datetime
from hashlib import sha256
import json

from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.resumable_market_batch import (
    FINAL_FAILURE_CATEGORIES,
    FINAL_FAILURE_POLICY_IDENTITY,
    ResumableMarketBatchService,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class ManifestTerminalSeriesIsolationService:
    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        selection: ManifestBatchSelection,
        checkpoint: object,
        *,
        normal_diagnostic_bytes: bytes,
        normal_diagnostic_checksum: str,
        repaired_qualification_bytes: bytes,
        repaired_qualification_checksum: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        if not isinstance(selection, ManifestBatchSelection):
            raise TypeError("selection must be a ManifestBatchSelection")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        normal_checksum, normal = _verified_report(
            normal_diagnostic_bytes,
            normal_diagnostic_checksum,
            field_name="normal_diagnostic_checksum",
        )
        repaired_checksum, repaired = _verified_report(
            repaired_qualification_bytes,
            repaired_qualification_checksum,
            field_name="repaired_qualification_checksum",
        )
        outcomes = ResumableMarketBatchService._outcomes(
            checkpoint, selection.request.checksum
        )
        items = {item.symbol: item for item in selection.request.items}
        if set(outcomes) != set(items):
            raise ValueError("Checkpoint outcomes do not exactly cover the request")

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
            transitioned_count = 1
            already_final_count = 0
            expected_failure_type = outcomes[symbol].get("failure_type")
        elif not retryable and len(final) == 1:
            symbol = final[0]
            transitioned_count = 0
            already_final_count = 1
            expected_failure_type = outcomes[symbol].get("failure_type")
        else:
            raise ValueError(
                "Checkpoint must contain exactly one retryable or final failure"
            )
        failure_type = normalize_required_text(
            expected_failure_type, field_name="failure_type"
        )

        normal_category = _normal_category(
            normal, selection, expected_failure_type=failure_type
        )
        repaired_category = _repaired_category(
            repaired, selection, expected_failure_type=failure_type
        )
        if normal_category != repaired_category:
            raise ValueError("Diagnostic failure categories do not match")
        if normal_category not in FINAL_FAILURE_CATEGORIES:
            raise ValueError("Failure category is not eligible for isolation")

        evidence = {
            "normal_diagnostic_checksum": normal_checksum,
            "repaired_qualification_checksum": repaired_checksum,
        }
        final_outcome = {
            "status": "FINAL_FAILED",
            "downloaded": None,
            "inserted": None,
            "duplicates": None,
            "omitted_trailing_count": 0,
            "omission_types": [],
            "failure_type": failure_type,
            "failure_category": normal_category,
            "isolation_policy_identity": FINAL_FAILURE_POLICY_IDENTITY,
            "isolation_evidence": evidence,
        }
        if already_final_count and outcomes[symbol] != final_outcome:
            raise ValueError("Existing final failure evidence does not match")
        outcomes[symbol] = final_outcome
        updated_checkpoint = {
            "schema_version": 3,
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
            "operation_identity": "MANIFEST_TERMINAL_SERIES_ISOLATION",
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
            "isolation_policy_identity": FINAL_FAILURE_POLICY_IDENTITY,
            "failure_category": normal_category,
            "evidence": evidence,
            "coverage": {
                "requested_count": len(selection.request.items),
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
                "terminal isolation applies only to this checksum-bound manifest request and does not authorize candle repair or persistence",
            ],
        }
        return updated_checkpoint, report


def _verified_report(
    raw: bytes, expected_checksum: str, *, field_name: str
) -> tuple[str, dict[str, object]]:
    if not isinstance(raw, bytes):
        raise TypeError("Report content must be bytes")
    expected = normalize_required_text(
        expected_checksum, field_name=field_name
    ).lower()
    if not _is_sha256(expected) or sha256(raw).hexdigest() != expected:
        raise ValueError(f"{field_name} does not match report bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda value: _reject_constant(value),
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Evidence report must contain strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("Evidence report must contain a JSON object")
    return expected, value


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Evidence report contains duplicate object keys")
        value[key] = item
    return value


def _normal_category(
    report: dict[str, object],
    selection: ManifestBatchSelection,
    *,
    expected_failure_type: str,
) -> str:
    _validate_common_report(
        report,
        selection,
        schema_version=3,
        identity_field="diagnostic_identity",
        identity="MANIFEST_FAILED_SERIES_RAW_CANDLE_DIAGNOSTIC",
        expected_failure_type=expected_failure_type,
    )
    coverage = report.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError("Normal diagnostic coverage is invalid")
    projection = coverage.get("strict_projection")
    if (
        not isinstance(projection, dict)
        or projection.get("status") != "REJECTED"
        or projection.get("projected_candle_count") is not None
    ):
        raise ValueError("Normal strict projection is not rejected")
    return normalize_required_text(
        projection.get("failure_category"),
        field_name="normal_failure_category",
        uppercase=True,
    )


def _repaired_category(
    report: dict[str, object],
    selection: ManifestBatchSelection,
    *,
    expected_failure_type: str,
) -> str:
    _validate_common_report(
        report,
        selection,
        schema_version=2,
        identity_field="qualification_identity",
        identity="MANIFEST_REPAIRED_SERIES_QUALIFICATION",
        expected_failure_type=expected_failure_type,
        expected_status="REJECTED",
    )
    repair = report.get("repair")
    if (
        not isinstance(repair, dict)
        or repair.get("method_identity") != "YFINANCE_PRICE_REPAIR_V1"
        or repair.get("requested") is not True
    ):
        raise ValueError("Explicit repaired retrieval evidence is invalid")
    coverage = report.get("coverage")
    if (
        not isinstance(coverage, dict)
        or coverage.get("projected_candle_count") is not None
    ):
        raise ValueError("Repaired strict projection is not rejected")
    return normalize_required_text(
        coverage.get("projection_failure_category"),
        field_name="repaired_failure_category",
        uppercase=True,
    )


def _validate_common_report(
    report: dict[str, object],
    selection: ManifestBatchSelection,
    *,
    schema_version: int,
    identity_field: str,
    identity: str,
    expected_failure_type: str,
    expected_status: str = "SUCCESS",
) -> None:
    expected = {
        "schema_version": schema_version,
        "provider_identity": "YAHOO_FINANCE",
        identity_field: identity,
        "status": expected_status,
        "manifest_checksum": selection.manifest_checksum,
        "batch_index": selection.batch_index,
        "batch_count": selection.batch_count,
        "request_checksum": selection.request.checksum,
        "requested_start": selection.request.start.isoformat(),
        "requested_end": selection.request.end.isoformat(),
        "failure": None,
    }
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError("Evidence report binding is invalid")
    selected = report.get("selection")
    if not isinstance(selected, dict) or selected.get("requested_count") != len(
        selection.request.items
    ):
        raise ValueError("Evidence selection is invalid")
    if (
        selected.get("failed_candidate_count") != 1
        or selected.get("selected_count") != 1
        or selected.get("checkpoint_failure_types") != [expected_failure_type]
    ):
        raise ValueError("Evidence failed-candidate binding is invalid")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
