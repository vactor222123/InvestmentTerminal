"""Sequential resumable ingestion for one bounded market-data batch."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    project_yahoo_candle_failure,
)
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


FINAL_FAILURE_POLICY_IDENTITY = "NORMAL_AND_REPAIRED_STRICT_REJECTION_V1"
FINAL_FAILURE_CATEGORIES = frozenset({"RESPONSE_NUMERIC", "RESPONSE_OHLC"})
NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY = "REPRODUCED_YAHOO_NO_PRICE_DATA_V1"
_PROJECTED_EXCEPTION_NAMESPACES = frozenset({
    "builtins", "curl_cffi", "investment_terminal", "numpy", "pandas",
    "peewee", "requests", "sqlite3", "urllib3", "yfinance",
})
_PROJECTED_EXCEPTION_SENTINELS = frozenset({
    "UNRECOGNIZED_EXCEPTION_TYPE", "EXCEPTION_CHAIN_TRUNCATED",
})


@dataclass(frozen=True, slots=True, order=True)
class MarketBatchItem:
    symbol: str
    currency: str


@dataclass(frozen=True, slots=True)
class MarketBatchRequest:
    resolution: str
    start: datetime
    end: datetime
    items: tuple[MarketBatchItem, ...]

    @classmethod
    def from_dict(cls, value: object) -> "MarketBatchRequest":
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise ValueError("Unsupported market batch request schema")
        resolution = normalize_required_text(value.get("resolution"), field_name="resolution", uppercase=True)
        if resolution not in {"D", "W", "M"}:
            raise ValueError("Unsupported resolution")
        start = _datetime(value.get("start"), "start")
        end = _datetime(value.get("end"), "end")
        if start >= end:
            raise ValueError("start must be earlier than end")
        rows = value.get("items")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 20 or any(not isinstance(row, dict) for row in rows):
            raise ValueError("items must contain between 1 and 20 objects")
        items = tuple(sorted(MarketBatchItem(
            normalize_required_text(row.get("symbol"), field_name="symbol", uppercase=True),
            normalize_required_text(row.get("currency"), field_name="currency", uppercase=True),
        ) for row in rows))
        if len({item.symbol for item in items}) != len(items):
            raise ValueError("items must contain unique symbols")
        return cls(resolution, start, end, items)

    def canonical_dict(self) -> dict[str, object]:
        return {"schema_version": 1, "resolution": self.resolution,
                "start": self.start.isoformat(), "end": self.end.isoformat(),
                "items": [{"symbol": x.symbol, "currency": x.currency} for x in self.items]}

    @property
    def checksum(self) -> str:
        raw = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(raw.encode("utf-8")).hexdigest()


class ResumableMarketBatchService:
    def __init__(self, *, importer, checkpoint_writer, clock) -> None:
        self.importer = importer
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(
        self,
        request: MarketBatchRequest,
        checkpoint: object | None = None,
        *,
        retry_failed: bool = True,
        continue_after_failure: Callable[[BaseException], bool] | None = None,
    ) -> dict[str, object]:
        if not isinstance(request, MarketBatchRequest):
            raise TypeError("request must be a MarketBatchRequest")
        if not isinstance(retry_failed, bool):
            raise TypeError("retry_failed must be a boolean")
        if continue_after_failure is not None and not callable(
            continue_after_failure
        ):
            raise TypeError("continue_after_failure must be callable or None")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        outcomes = self._outcomes(checkpoint, request.checksum)
        checkpoint_schema = checkpoint.get("schema_version") if isinstance(checkpoint, dict) else None
        skipped = 0
        current_outcomes: list[dict[str, object]] = []
        for item in request.items:
            previous = outcomes.get(item.symbol)
            if previous is not None and previous["status"] in {
                "SUCCESS", "EMPTY", "FINAL_FAILED"
            } or (
                previous is not None
                and previous["status"] == "FAILED"
                and not retry_failed
            ):
                skipped += 1
                continue
            failure = None
            try:
                result = self.importer.import_candles(
                    symbol=item.symbol, resolution=request.resolution,
                    start=request.start, end=request.end, currency=item.currency)
                status = "SUCCESS" if result.downloaded else "EMPTY"
                omitted, omission_types = _omission_evidence(result)
                outcomes[item.symbol] = {"status": status, "downloaded": result.downloaded,
                    "inserted": result.inserted, "duplicates": result.duplicates,
                    "omitted_trailing_count": omitted,
                    "omission_types": list(omission_types), "failure_type": None}
            except Exception as exc:
                failure = exc
                causal = project_yahoo_candle_failure(exc)
                outcomes[item.symbol] = {"status": "FAILED", "downloaded": None,
                    "inserted": None, "duplicates": None,
                    "omitted_trailing_count": 0, "omission_types": [],
                    "failure_type": type(exc).__name__,
                    "causal_failure_evidence": {
                        "category": causal.category.value,
                        "exception_type_chain": list(causal.exception_type_chain),
                    }}
            current_outcomes.append(outcomes[item.symbol])
            if checkpoint_schema in {1, 2, 3}:
                for outcome in outcomes.values():
                    if outcome["status"] == "FAILED":
                        outcome.setdefault("causal_failure_evidence", None)
            self.checkpoint_writer({"schema_version": 4, "request_checksum": request.checksum,
                                    "outcomes": outcomes})
            checkpoint_schema = 4
            if (
                failure is not None
                and continue_after_failure is not None
                and not continue_after_failure(failure)
            ):
                raise failure
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        values = [outcomes[item.symbol] for item in request.items]
        success = sum(x["status"] == "SUCCESS" for x in values)
        empty = sum(x["status"] == "EMPTY" for x in values)
        failed = sum(x["status"] == "FAILED" for x in values)
        final_failed = sum(x["status"] == "FINAL_FAILED" for x in values)
        if failed == 0:
            status = "SUCCESS_WITH_EXCLUSIONS" if final_failed else "SUCCESS"
        else:
            status = "PARTIAL" if success + empty + final_failed else "FAILED"
        return {"schema_version": 4, "provider_identity": "YAHOO_FINANCE", "status": status,
            "started_at": started.isoformat(), "completed_at": completed.isoformat(),
            "duration_seconds": (completed-started).total_seconds(), "coverage": {
                "current_run": {"attempted_count": len(current_outcomes), "skipped_count": skipped,
                    "downloaded_total": sum(x["downloaded"] or 0 for x in current_outcomes),
                    "inserted_total": sum(x["inserted"] or 0 for x in current_outcomes),
                    "duplicate_total": sum(x["duplicates"] or 0 for x in current_outcomes),
                    "omitted_trailing_total": sum(x["omitted_trailing_count"] for x in current_outcomes),
                    "omission_types": _omission_types(current_outcomes)},
                "cumulative": {"requested_count": len(request.items), "success_count": success,
                    "empty_count": empty, "retryable_failure_count": failed,
                    "final_failure_count": final_failed,
                    "downloaded_total": sum(x["downloaded"] or 0 for x in values),
                    "inserted_total": sum(x["inserted"] or 0 for x in values),
                    "duplicate_total": sum(x["duplicates"] or 0 for x in values),
                    "omitted_trailing_total": sum(x["omitted_trailing_count"] for x in values),
                    "omission_types": _omission_types(values)}},
            "failure_types": sorted({x["failure_type"] for x in values
                                     if x["status"] == "FAILED" and x["failure_type"]}),
            "final_failure_categories": sorted({x["failure_category"] for x in values
                                                if x["status"] == "FINAL_FAILED"}),
            "limitations": ["report excludes symbols, paths, prices, provider text, and exception messages",
                            "batch execution does not authorize scheduling, mass ingestion, analysis, or trading"]}

    @staticmethod
    def _outcomes(value: object | None, checksum: str) -> dict[str, dict[str, object]]:
        if value is None:
            return {}
        if not isinstance(value, dict) or value.get("schema_version") not in {1, 2, 3, 4} or value.get("request_checksum") != checksum:
            raise ValueError("Checkpoint does not match request")
        outcomes = value.get("outcomes")
        if not isinstance(outcomes, dict) or any(not isinstance(k, str) or not isinstance(v, dict) for k, v in outcomes.items()):
            raise ValueError("Checkpoint outcomes are invalid")
        normalized = {}
        for key, outcome in outcomes.items():
            item = dict(outcome)
            if value["schema_version"] == 1:
                item["omitted_trailing_count"] = 0
                item["omission_types"] = []
            _validate_outcome_omission(item)
            _validate_outcome_status(item, schema_version=value["schema_version"])
            normalized[key] = item
        return normalized


def _omission_evidence(result) -> tuple[int, tuple[str, ...]]:
    count = getattr(result, "omitted_trailing_count", 0)
    types = getattr(result, "omission_types", ())
    candidate = {"omitted_trailing_count": count, "omission_types": list(types)}
    _validate_outcome_omission(candidate)
    return count, tuple(types)


def _validate_outcome_omission(outcome: dict[str, object]) -> None:
    count = outcome.get("omitted_trailing_count")
    types = outcome.get("omission_types")
    if isinstance(count, bool) or count not in {0, 1} or not isinstance(types, list):
        raise ValueError("Checkpoint omission evidence is invalid")
    expected = ["TRAILING_NON_FINITE_NUMERIC"] if count else []
    if types != expected:
        raise ValueError("Checkpoint omission evidence is inconsistent")


def _omission_types(outcomes) -> list[str]:
    return sorted({item for outcome in outcomes for item in outcome["omission_types"]})


def _validate_outcome_status(
    outcome: dict[str, object], *, schema_version: int
) -> None:
    status = outcome.get("status")
    if status not in {"SUCCESS", "EMPTY", "FAILED", "FINAL_FAILED"}:
        raise ValueError("Checkpoint outcome status is invalid")
    causal_field = "causal_failure_evidence"
    if schema_version == 4 and status == "FAILED":
        if causal_field not in outcome:
            raise ValueError("Schema-4 failure requires causal evidence")
        _validate_causal_failure_evidence(outcome[causal_field])
    elif causal_field in outcome:
        raise ValueError("Checkpoint outcome has invalid causal evidence")
    final_fields = {
        "failure_category",
        "isolation_policy_identity",
        "isolation_evidence",
    }
    if status != "FINAL_FAILED":
        if any(field in outcome for field in final_fields):
            raise ValueError("Non-final checkpoint outcome has isolation evidence")
        return
    if schema_version not in {3, 4}:
        raise ValueError("FINAL_FAILED requires checkpoint schema version 3 or 4")
    if any(outcome.get(field) is not None for field in ("downloaded", "inserted", "duplicates")):
        raise ValueError("FINAL_FAILED transfer counts must be null")
    failure_type = outcome.get("failure_type")
    if not isinstance(failure_type, str) or not failure_type.strip():
        raise ValueError("FINAL_FAILED requires a failure type")
    category = outcome.get("failure_category")
    policy = outcome.get("isolation_policy_identity")
    evidence = outcome.get("isolation_evidence")
    if policy == FINAL_FAILURE_POLICY_IDENTITY:
        if category not in FINAL_FAILURE_CATEGORIES:
            raise ValueError("FINAL_FAILED category is invalid")
        expected_evidence = {
            "normal_diagnostic_checksum", "repaired_qualification_checksum",
        }
    elif schema_version == 4 and policy == NO_PRICE_FINAL_FAILURE_POLICY_IDENTITY:
        if category != "NO_PRICE_DATA" or failure_type != "APIError":
            raise ValueError("FINAL_FAILED no-price evidence is invalid")
        expected_evidence = {"partial_failure_qualification_checksum"}
    else:
        raise ValueError("FINAL_FAILED policy identity is invalid")
    if not isinstance(evidence, dict) or set(evidence) != expected_evidence:
        raise ValueError("FINAL_FAILED isolation evidence is invalid")
    if any(not _is_sha256(value) for value in evidence.values()):
        raise ValueError("FINAL_FAILED evidence checksum is invalid")


def _validate_causal_failure_evidence(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict) or set(value) != {
        "category", "exception_type_chain",
    }:
        raise ValueError("Checkpoint causal evidence is invalid")
    try:
        YahooCandleFailureCategory(value.get("category"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Checkpoint causal category is invalid") from exc
    chain = value.get("exception_type_chain")
    if (
        not isinstance(chain, list)
        or not 1 <= len(chain) <= 8
        or any(not _is_projected_exception_type(item) for item in chain)
        or "EXCEPTION_CHAIN_TRUNCATED" in chain[:-1]
    ):
        raise ValueError("Checkpoint causal type chain is invalid")


def _is_projected_exception_type(value: object) -> bool:
    if isinstance(value, str) and value in _PROJECTED_EXCEPTION_SENTINELS:
        return True
    if not isinstance(value, str) or "." not in value:
        return False
    segments = value.split(".")
    return segments[0] in _PROJECTED_EXCEPTION_NAMESPACES and all(
        _is_ascii_identifier(segment) for segment in segments
    )


def _is_ascii_identifier(value: str) -> bool:
    if not value:
        return False
    first, remainder = value[0], value[1:]
    return (first == "_" or first.isascii() and first.isalpha()) and all(
        character == "_" or character.isascii() and character.isalnum()
        for character in remainder
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO-8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    return validate_aware_datetime(parsed, field_name=field_name)
