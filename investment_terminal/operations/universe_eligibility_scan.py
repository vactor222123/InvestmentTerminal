"""Bounded resumable market-universe eligibility measurement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from math import isfinite
from statistics import median

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    classify_yahoo_candle_failure,
)
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


_TERMINAL_STATUSES = frozenset({"SUCCESS", "EMPTY", "FINAL_FAILED", "PROJECTION_FAILED"})
_ALL_STATUSES = _TERMINAL_STATUSES | {"RETRY_PENDING"}
_RETRYABLE_CATEGORIES = frozenset({
    "UNKNOWN_LEGACY_API_ERROR",
    YahooCandleFailureCategory.RATE_LIMITED.value,
    YahooCandleFailureCategory.TIMEOUT.value,
    YahooCandleFailureCategory.TRANSPORT_FAILURE.value,
})
_FINAL_CATEGORIES = frozenset({
    YahooCandleFailureCategory.NO_PRICE_DATA.value,
    YahooCandleFailureCategory.INVALID_REQUEST.value,
    YahooCandleFailureCategory.INVALID_RESPONSE.value,
    YahooCandleFailureCategory.PROVIDER_FAILURE.value,
    YahooCandleFailureCategory.UNEXPECTED.value,
})
_FAILURE_CATEGORIES = _RETRYABLE_CATEGORIES | _FINAL_CATEGORIES | {"PROJECTION_UNAVAILABLE"}
_MAX_PROVIDER_ATTEMPTS = 3


@dataclass(frozen=True, slots=True, order=True)
class EligibilityMember:
    yahoo_symbol: str
    source: str
    source_symbol: str

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_symbol}"


@dataclass(frozen=True, slots=True)
class EligibilityScanRequest:
    universe_checksum: str
    requested_start: datetime
    requested_end: datetime
    members: tuple[EligibilityMember, ...]

    @classmethod
    def from_universe(cls, value: object, *, requested_end: datetime) -> "EligibilityScanRequest":
        end = validate_aware_datetime(requested_end, field_name="requested_end")
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise ValueError("Unsupported private universe schema")
        if value.get("universe_identity") != "BROAD_US_LISTED_SECURITIES":
            raise ValueError("Unsupported universe identity")
        if value.get("source_identity") != "NASDAQ_TRADER_SYMBOL_DIRECTORY":
            raise ValueError("Unsupported universe source identity")
        archives = value.get("archive_sha256")
        if (not isinstance(archives, dict) or set(archives) != {"NASDAQ_LISTED", "OTHER_LISTED"}
                or any(not _is_sha256(item) for item in archives.values())):
            raise ValueError("Universe archive evidence is invalid")
        rows = value.get("members")
        if not isinstance(rows, list) or not rows:
            raise ValueError("Universe members must be a non-empty list")
        members = []
        canonical_rows = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Universe member must be an object")
            source = normalize_required_text(row.get("source"), field_name="source", uppercase=True)
            if source not in {"NASDAQ_LISTED", "OTHER_LISTED"}:
                raise ValueError("Universe member source is invalid")
            source_symbol = normalize_required_text(row.get("source_symbol"), field_name="source_symbol", uppercase=True)
            yahoo_value = row.get("yahoo_symbol")
            yahoo_symbol = (normalize_required_text(yahoo_value, field_name="yahoo_symbol", uppercase=True)
                            if yahoo_value is not None else "")
            listing_code = normalize_required_text(row.get("listing_code"), field_name="listing_code", uppercase=True)
            security_name = normalize_required_text(row.get("security_name"), field_name="security_name")
            is_etf = row.get("is_etf")
            if not isinstance(is_etf, bool):
                raise ValueError("is_etf must be a bool")
            members.append(EligibilityMember(yahoo_symbol, source, source_symbol))
            canonical_rows.append({"source": source, "source_symbol": source_symbol,
                "yahoo_symbol": yahoo_symbol or None, "security_name": security_name,
                "listing_code": listing_code, "is_etf": is_etf})
        ordered = tuple(sorted(members))
        if len({item.key for item in ordered}) != len(ordered):
            raise ValueError("Universe member identities must be unique")
        projected = [item.yahoo_symbol for item in ordered if item.yahoo_symbol]
        if len(set(projected)) != len(projected):
            raise ValueError("Projected Yahoo symbols must be unique")
        canonical = {"schema_version": 1, "universe_identity": value["universe_identity"],
            "source_identity": value["source_identity"],
            "archive_sha256": {key: archives[key] for key in sorted(archives)},
            "members": sorted(canonical_rows, key=lambda item: (
                str(item["yahoo_symbol"] or ""), str(item["source"]), str(item["source_symbol"]))) }
        return cls(_checksum(canonical), end - timedelta(days=90), end, ordered)

    @property
    def checksum(self) -> str:
        return _checksum({"schema_version": 1, "universe_checksum": self.universe_checksum,
            "requested_start": self.requested_start.isoformat(),
            "requested_end": self.requested_end.isoformat()})


class UniverseEligibilityScanService:
    """Migrate, retry, and process one deterministic bounded scan slice."""

    def __init__(self, *, client, checkpoint_writer, clock) -> None:
        self.client = client
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(self, request: EligibilityScanRequest, checkpoint: object | None = None,
            *, max_items: int = 100) -> dict[str, object]:
        if not isinstance(request, EligibilityScanRequest):
            raise TypeError("request must be an EligibilityScanRequest")
        if isinstance(max_items, bool) or not isinstance(max_items, int):
            raise TypeError("max_items must be an integer")
        if not 1 <= max_items <= 100:
            raise ValueError("max_items must be between 1 and 100")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        outcomes, migrated_count = self._outcomes(checkpoint, request)
        if migrated_count:
            self.checkpoint_writer(self._checkpoint_payload(request, outcomes))
        retry_members = [item for item in request.members
            if outcomes.get(item.key, {}).get("status") == "RETRY_PENDING"]
        new_members = [item for item in request.members if item.key not in outcomes]
        attempted = 0
        provider_requests = 0
        halt_category = None
        for member in retry_members + new_members:
            if attempted >= max_items:
                break
            previous = outcomes.get(member.key)
            attempted += 1
            measured_at = validate_aware_datetime(self.clock(), field_name="measured_at")
            if not member.yahoo_symbol:
                outcome = self._projection_failure(member, measured_at)
            else:
                provider_requests += 1
                outcome = self._measure(request, member, measured_at,
                    previous_attempt_count=int(previous["attempt_count"]) if previous else 0)
            outcomes[member.key] = outcome
            self.checkpoint_writer(self._checkpoint_payload(request, outcomes))
            if outcome.get("failure_category") == "RATE_LIMITED":
                halt_category = "RATE_LIMITED"
                break
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        counts = {status: sum(item["status"] == status for item in outcomes.values())
                  for status in sorted(_ALL_STATUSES)}
        terminal = sum(counts[item] for item in _TERMINAL_STATUSES)
        retry_pending = counts["RETRY_PENDING"]
        never_attempted = len(request.members) - len(outcomes)
        status = "PAUSED" if halt_category else (
            "COMPLETE" if terminal == len(request.members) else "IN_PROGRESS")
        categories = {}
        for outcome in outcomes.values():
            category = outcome.get("failure_category")
            if category is not None:
                categories[str(category)] = categories.get(str(category), 0) + 1
        return {"schema_version": 2, "provider_identity": "YAHOO_FINANCE",
            "universe_identity": "BROAD_US_LISTED_SECURITIES", "status": status,
            "started_at": started.isoformat(), "completed_at": completed.isoformat(),
            "duration_seconds": (completed-started).total_seconds(),
            "request_checksum": request.checksum, "universe_checksum": request.universe_checksum,
            "requested_start": request.requested_start.isoformat(),
            "requested_end": request.requested_end.isoformat(),
            "coverage": {"current_run": {"attempted_count": attempted,
                "provider_request_count": provider_requests, "migrated_outcome_count": migrated_count},
                "cumulative": {"member_count": len(request.members), "terminal_count": terminal,
                    "retry_pending_count": retry_pending, "never_attempted_count": never_attempted,
                    "pending_count": retry_pending + never_attempted,
                    "success_count": counts["SUCCESS"], "empty_count": counts["EMPTY"],
                    "final_failure_count": counts["FINAL_FAILED"],
                    "projection_failure_count": counts["PROJECTION_FAILED"]}},
            "failure_categories": {key: categories[key] for key in sorted(categories)},
            "halt_category": halt_category, "failure": None,
            "limitations": ["report excludes symbols, names, prices, paths, provider text, and exception messages",
                "eligibility progress does not rank members or authorize historical ingestion"]}

    def _measure(self, request, member, measured_at, *, previous_attempt_count):
        attempt_count = previous_attempt_count + 1
        try:
            candles = self.client.get_candles(symbol=member.yahoo_symbol, resolution="D",
                start=request.requested_start, end=request.requested_end, currency="USD")
            if not isinstance(candles, list):
                raise TypeError("Provider candles must be a list")
            timestamps = []
            values = []
            positive_days = 0
            for candle in candles:
                if candle.symbol != member.yahoo_symbol or candle.resolution != "D" or candle.currency != "USD":
                    raise ValueError("Provider candle identity mismatch")
                timestamp = validate_aware_datetime(candle.timestamp, field_name="candle.timestamp")
                if not request.requested_start <= timestamp < request.requested_end:
                    raise ValueError("Provider candle is outside the request window")
                close = _finite_number(candle.close_price, "close_price")
                volume = _finite_number(candle.volume, "volume")
                if close <= 0 or volume < 0:
                    raise ValueError("Provider candle values are invalid")
                timestamps.append(timestamp)
                positive_days += volume > 0
                values.append(close * volume)
            if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
                raise ValueError("Provider candles must be unique and ordered")
            return {**self._identity(member), "status": "SUCCESS" if candles else "EMPTY",
                "attempt_count": attempt_count, "provider_instrument_type": None,
                "observed_start": timestamps[0].isoformat() if timestamps else None,
                "observed_end": timestamps[-1].isoformat() if timestamps else None,
                "candle_count": len(candles), "positive_volume_day_count": positive_days,
                "median_daily_traded_value": float(median(values)) if values else None,
                "measured_at": measured_at.isoformat(), "failure_category": None}
        except Exception as exc:
            category = classify_yahoo_candle_failure(exc).value
            status = ("RETRY_PENDING" if category in _RETRYABLE_CATEGORIES
                      and attempt_count < _MAX_PROVIDER_ATTEMPTS else "FINAL_FAILED")
            return {**self._identity(member), "status": status, "attempt_count": attempt_count,
                "provider_instrument_type": None, "observed_start": None, "observed_end": None,
                "candle_count": None, "positive_volume_day_count": None,
                "median_daily_traded_value": None, "measured_at": measured_at.isoformat(),
                "failure_category": category}

    @staticmethod
    def _identity(member):
        return {"source": member.source, "source_symbol": member.source_symbol,
                "yahoo_symbol": member.yahoo_symbol or None}

    @classmethod
    def _projection_failure(cls, member, measured_at):
        return {**cls._identity(member), "status": "PROJECTION_FAILED", "attempt_count": 0,
            "provider_instrument_type": None, "observed_start": None, "observed_end": None,
            "candle_count": None, "positive_volume_day_count": None,
            "median_daily_traded_value": None, "measured_at": measured_at.isoformat(),
            "failure_category": "PROJECTION_UNAVAILABLE"}

    @staticmethod
    def _checkpoint_payload(request, outcomes):
        return {"schema_version": 2, "request_checksum": request.checksum,
            "universe_checksum": request.universe_checksum,
            "requested_start": request.requested_start.isoformat(),
            "requested_end": request.requested_end.isoformat(),
            "outcomes": {key: outcomes[key] for key in sorted(outcomes)}}

    @classmethod
    def _outcomes(cls, value, request):
        if value is None:
            return {}, 0
        if not isinstance(value, dict) or value.get("schema_version") not in {1, 2}:
            raise ValueError("Unsupported eligibility checkpoint schema")
        if (value.get("request_checksum") != request.checksum
                or value.get("universe_checksum") != request.universe_checksum
                or value.get("requested_start") != request.requested_start.isoformat()
                or value.get("requested_end") != request.requested_end.isoformat()):
            raise ValueError("Checkpoint does not match eligibility request")
        raw = value.get("outcomes")
        if not isinstance(raw, dict):
            raise ValueError("Checkpoint outcomes are invalid")
        members = {item.key: item for item in request.members}
        outcomes = {}
        for key, outcome in raw.items():
            if not isinstance(key, str) or key not in members or not isinstance(outcome, dict):
                raise ValueError("Checkpoint outcome identity is invalid")
            if value["schema_version"] == 1:
                cls._validate_v1(outcome, members[key])
                outcomes[key] = cls._migrate_v1(outcome, members[key])
            else:
                cls._validate_v2(outcome, members[key])
                outcomes[key] = dict(outcome)
        return outcomes, len(outcomes) if value["schema_version"] == 1 else 0

    @classmethod
    def _migrate_v1(cls, value, member):
        base = {**cls._identity(member), "provider_instrument_type": value.get("provider_instrument_type"),
            "observed_start": value.get("observed_start"), "observed_end": value.get("observed_end"),
            "candle_count": value.get("candle_count"),
            "positive_volume_day_count": value.get("positive_volume_day_count"),
            "median_daily_traded_value": value.get("median_daily_traded_value"),
            "measured_at": value["measured_at"]}
        if value["status"] in {"SUCCESS", "EMPTY"}:
            return {**base, "status": value["status"], "attempt_count": 1, "failure_category": None}
        if value["status"] == "PROJECTION_FAILED":
            return {**base, "status": "PROJECTION_FAILED", "attempt_count": 0,
                    "failure_category": "PROJECTION_UNAVAILABLE"}
        if value["failure_type"] == "APIError":
            return {**base, "status": "RETRY_PENDING", "attempt_count": 1,
                    "failure_category": "UNKNOWN_LEGACY_API_ERROR"}
        if value["failure_type"] == "TimeoutError":
            return {**base, "status": "RETRY_PENDING", "attempt_count": 1,
                    "failure_category": "TIMEOUT"}
        return {**base, "status": "FINAL_FAILED", "attempt_count": 1,
                "failure_category": "UNEXPECTED"}

    @classmethod
    def _validate_v1(cls, value, member):
        status = value.get("status")
        if status not in {"SUCCESS", "EMPTY", "FAILED", "PROJECTION_FAILED"}:
            raise ValueError("Schema-1 checkpoint status is invalid")
        cls._validate_identity_time(value, member)
        if status == "SUCCESS": cls._validate_success(value)
        elif status == "EMPTY": cls._validate_empty(value)
        elif not isinstance(value.get("failure_type"), str):
            raise ValueError("Schema-1 checkpoint failure type is invalid")

    @classmethod
    def _validate_v2(cls, value, member):
        status = value.get("status")
        if status not in _ALL_STATUSES:
            raise ValueError("Schema-2 checkpoint status is invalid")
        cls._validate_identity_time(value, member)
        attempts = value.get("attempt_count")
        if isinstance(attempts, bool) or not isinstance(attempts, int) or not 0 <= attempts <= 3:
            raise ValueError("Schema-2 checkpoint attempt count is invalid")
        category = value.get("failure_category")
        if status == "SUCCESS":
            cls._validate_success(value)
            if category is not None or attempts < 1: raise ValueError("Successful schema-2 outcome is invalid")
        elif status == "EMPTY":
            cls._validate_empty(value)
            if category is not None or attempts < 1: raise ValueError("Empty schema-2 outcome is invalid")
        elif status == "PROJECTION_FAILED":
            if category != "PROJECTION_UNAVAILABLE" or attempts != 0: raise ValueError("Projection schema-2 outcome is invalid")
        elif not isinstance(category, str) or category not in _FAILURE_CATEGORIES:
            raise ValueError("Schema-2 failure category is invalid")
        elif status == "RETRY_PENDING" and (category not in _RETRYABLE_CATEGORIES or attempts < 1 or attempts >= 3):
            raise ValueError("Retry-pending schema-2 outcome is invalid")
        elif status == "FINAL_FAILED" and attempts < 1:
            raise ValueError("Final schema-2 outcome is invalid")

    @staticmethod
    def _validate_identity_time(value, member):
        if (value.get("source") != member.source or value.get("source_symbol") != member.source_symbol
                or value.get("yahoo_symbol") != (member.yahoo_symbol or None)):
            raise ValueError("Checkpoint outcome does not match universe member")
        measured = value.get("measured_at")
        if not isinstance(measured, str): raise ValueError("Checkpoint outcome measured_at is invalid")
        try: parsed = datetime.fromisoformat(measured.replace("Z", "+00:00"))
        except ValueError as exc: raise ValueError("Checkpoint outcome measured_at is invalid") from exc
        validate_aware_datetime(parsed, field_name="measured_at")

    @staticmethod
    def _validate_success(value):
        count = value.get("candle_count"); positive = value.get("positive_volume_day_count")
        if (isinstance(count, bool) or not isinstance(count, int) or count < 1
                or isinstance(positive, bool) or not isinstance(positive, int) or not 0 <= positive <= count
                or _finite_number(value.get("median_daily_traded_value"), "median_daily_traded_value") < 0):
            raise ValueError("Successful checkpoint metrics are invalid")

    @staticmethod
    def _validate_empty(value):
        if (value.get("candle_count") != 0 or value.get("positive_volume_day_count") != 0
                or value.get("median_daily_traded_value") is not None):
            raise ValueError("Empty checkpoint metrics are invalid")


def _is_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _checksum(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                             allow_nan=False).encode("utf-8")).hexdigest()


def _finite_number(value, field_name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number")
    result = float(value)
    if not isfinite(result): raise ValueError(f"{field_name} must be a finite number")
    return result
