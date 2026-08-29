"""Bounded resumable market-universe eligibility measurement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from math import isfinite
from statistics import median

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


_TERMINAL_STATUSES = frozenset(
    {"SUCCESS", "EMPTY", "FAILED", "PROJECTION_FAILED"}
)


@dataclass(frozen=True, slots=True, order=True)
class EligibilityMember:
    """Private provider identity selected from the qualified universe."""

    yahoo_symbol: str
    source: str
    source_symbol: str

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_symbol}"


@dataclass(frozen=True, slots=True)
class EligibilityScanRequest:
    """One complete-universe eligibility request with a fixed time window."""

    universe_checksum: str
    requested_start: datetime
    requested_end: datetime
    members: tuple[EligibilityMember, ...]

    @classmethod
    def from_universe(
        cls,
        value: object,
        *,
        requested_end: datetime,
    ) -> "EligibilityScanRequest":
        end = validate_aware_datetime(
            requested_end,
            field_name="requested_end",
        )
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise ValueError("Unsupported private universe schema")
        if value.get("universe_identity") != "BROAD_US_LISTED_SECURITIES":
            raise ValueError("Unsupported universe identity")
        if value.get("source_identity") != "NASDAQ_TRADER_SYMBOL_DIRECTORY":
            raise ValueError("Unsupported universe source identity")

        archive_sha256 = value.get("archive_sha256")
        if (
            not isinstance(archive_sha256, dict)
            or set(archive_sha256) != {"NASDAQ_LISTED", "OTHER_LISTED"}
            or any(not _is_sha256(item) for item in archive_sha256.values())
        ):
            raise ValueError("Universe archive evidence is invalid")

        rows = value.get("members")
        if not isinstance(rows, list) or not rows:
            raise ValueError("Universe members must be a non-empty list")

        members: list[EligibilityMember] = []
        canonical_rows: list[dict[str, object]] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Universe member must be an object")
            source = normalize_required_text(
                row.get("source"),
                field_name="source",
                uppercase=True,
            )
            if source not in {"NASDAQ_LISTED", "OTHER_LISTED"}:
                raise ValueError("Universe member source is invalid")
            source_symbol = normalize_required_text(
                row.get("source_symbol"),
                field_name="source_symbol",
                uppercase=True,
            )
            yahoo_value = row.get("yahoo_symbol")
            yahoo_symbol = (
                normalize_required_text(
                    yahoo_value,
                    field_name="yahoo_symbol",
                    uppercase=True,
                )
                if yahoo_value is not None
                else ""
            )
            listing_code = normalize_required_text(
                row.get("listing_code"),
                field_name="listing_code",
                uppercase=True,
            )
            security_name = normalize_required_text(
                row.get("security_name"),
                field_name="security_name",
            )
            is_etf = row.get("is_etf")
            if not isinstance(is_etf, bool):
                raise ValueError("is_etf must be a bool")
            members.append(
                EligibilityMember(
                    yahoo_symbol=yahoo_symbol,
                    source=source,
                    source_symbol=source_symbol,
                )
            )
            canonical_rows.append(
                {
                    "source": source,
                    "source_symbol": source_symbol,
                    "yahoo_symbol": yahoo_symbol or None,
                    "security_name": security_name,
                    "listing_code": listing_code,
                    "is_etf": is_etf,
                }
            )

        ordered_members = tuple(sorted(members))
        if len({member.key for member in ordered_members}) != len(ordered_members):
            raise ValueError("Universe member identities must be unique")
        projected = [member.yahoo_symbol for member in ordered_members if member.yahoo_symbol]
        if len(set(projected)) != len(projected):
            raise ValueError("Projected Yahoo symbols must be unique")

        canonical = {
            "schema_version": 1,
            "universe_identity": value["universe_identity"],
            "source_identity": value["source_identity"],
            "archive_sha256": {
                key: archive_sha256[key]
                for key in sorted(archive_sha256)
            },
            "members": sorted(
                canonical_rows,
                key=lambda item: (
                    str(item["yahoo_symbol"] or ""),
                    str(item["source"]),
                    str(item["source_symbol"]),
                ),
            ),
        }
        universe_checksum = _checksum(canonical)
        return cls(
            universe_checksum=universe_checksum,
            requested_start=end - timedelta(days=90),
            requested_end=end,
            members=ordered_members,
        )

    @property
    def checksum(self) -> str:
        return _checksum(
            {
                "schema_version": 1,
                "universe_checksum": self.universe_checksum,
                "requested_start": self.requested_start.isoformat(),
                "requested_end": self.requested_end.isoformat(),
            }
        )


class UniverseEligibilityScanService:
    """Process one deterministic bounded slice and checkpoint every outcome."""

    def __init__(self, *, client, checkpoint_writer, clock) -> None:
        self.client = client
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(
        self,
        request: EligibilityScanRequest,
        checkpoint: object | None = None,
        *,
        max_items: int = 100,
    ) -> dict[str, object]:
        if not isinstance(request, EligibilityScanRequest):
            raise TypeError("request must be an EligibilityScanRequest")
        if isinstance(max_items, bool) or not isinstance(max_items, int):
            raise TypeError("max_items must be an integer")
        if not 1 <= max_items <= 100:
            raise ValueError("max_items must be between 1 and 100")

        started = validate_aware_datetime(self.clock(), field_name="started_at")
        outcomes = self._outcomes(checkpoint, request)
        attempted = 0
        provider_requests = 0

        for member in request.members:
            if member.key in outcomes:
                continue
            if attempted >= max_items:
                break
            attempted += 1
            measured_at = validate_aware_datetime(
                self.clock(),
                field_name="measured_at",
            )
            if not member.yahoo_symbol:
                outcome = self._projection_failure(member, measured_at)
            else:
                provider_requests += 1
                outcome = self._measure(request, member, measured_at)
            outcomes[member.key] = outcome
            self.checkpoint_writer(
                self._checkpoint_payload(request, outcomes)
            )

        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        counts = {
            status: sum(item["status"] == status for item in outcomes.values())
            for status in sorted(_TERMINAL_STATUSES)
        }
        terminal_count = len(outcomes)
        pending_count = len(request.members) - terminal_count
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "universe_identity": "BROAD_US_LISTED_SECURITIES",
            "status": "COMPLETE" if pending_count == 0 else "IN_PROGRESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "request_checksum": request.checksum,
            "universe_checksum": request.universe_checksum,
            "requested_start": request.requested_start.isoformat(),
            "requested_end": request.requested_end.isoformat(),
            "coverage": {
                "current_run": {
                    "attempted_count": attempted,
                    "provider_request_count": provider_requests,
                    "resumed_terminal_count": terminal_count - attempted,
                },
                "cumulative": {
                    "member_count": len(request.members),
                    "terminal_count": terminal_count,
                    "pending_count": pending_count,
                    "success_count": counts["SUCCESS"],
                    "empty_count": counts["EMPTY"],
                    "failure_count": counts["FAILED"],
                    "projection_failure_count": counts["PROJECTION_FAILED"],
                },
            },
            "failure_types": sorted(
                {
                    str(item["failure_type"])
                    for item in outcomes.values()
                    if item["failure_type"] is not None
                }
            ),
            "failure": None,
            "limitations": [
                "report excludes symbols, names, prices, paths, provider text, and exception messages",
                "eligibility progress does not rank members or authorize historical ingestion",
            ],
        }

    def _measure(
        self,
        request: EligibilityScanRequest,
        member: EligibilityMember,
        measured_at: datetime,
    ) -> dict[str, object]:
        try:
            candles = self.client.get_candles(
                symbol=member.yahoo_symbol,
                resolution="D",
                start=request.requested_start,
                end=request.requested_end,
                currency="USD",
            )
            if not isinstance(candles, list):
                raise TypeError("Provider candles must be a list")
            timestamps: list[datetime] = []
            traded_values: list[float] = []
            positive_volume_days = 0
            for candle in candles:
                if (
                    candle.symbol != member.yahoo_symbol
                    or candle.resolution != "D"
                    or candle.currency != "USD"
                ):
                    raise ValueError("Provider candle identity mismatch")
                timestamp = validate_aware_datetime(
                    candle.timestamp,
                    field_name="candle.timestamp",
                )
                if not request.requested_start <= timestamp < request.requested_end:
                    raise ValueError("Provider candle is outside the request window")
                close = _finite_number(candle.close_price, "close_price")
                volume = _finite_number(candle.volume, "volume")
                if close <= 0 or volume < 0:
                    raise ValueError("Provider candle values are invalid")
                timestamps.append(timestamp)
                if volume > 0:
                    positive_volume_days += 1
                traded_values.append(close * volume)
            if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
                raise ValueError("Provider candles must be unique and ordered")
            status = "SUCCESS" if candles else "EMPTY"
            return {
                "source": member.source,
                "source_symbol": member.source_symbol,
                "yahoo_symbol": member.yahoo_symbol,
                "status": status,
                "provider_instrument_type": None,
                "observed_start": timestamps[0].isoformat() if timestamps else None,
                "observed_end": timestamps[-1].isoformat() if timestamps else None,
                "candle_count": len(candles),
                "positive_volume_day_count": positive_volume_days,
                "median_daily_traded_value": float(median(traded_values)) if traded_values else None,
                "measured_at": measured_at.isoformat(),
                "failure_type": None,
            }
        except Exception as exc:
            return {
                "source": member.source,
                "source_symbol": member.source_symbol,
                "yahoo_symbol": member.yahoo_symbol,
                "status": "FAILED",
                "provider_instrument_type": None,
                "observed_start": None,
                "observed_end": None,
                "candle_count": None,
                "positive_volume_day_count": None,
                "median_daily_traded_value": None,
                "measured_at": measured_at.isoformat(),
                "failure_type": type(exc).__name__,
            }

    @staticmethod
    def _projection_failure(
        member: EligibilityMember,
        measured_at: datetime,
    ) -> dict[str, object]:
        return {
            "source": member.source,
            "source_symbol": member.source_symbol,
            "yahoo_symbol": None,
            "status": "PROJECTION_FAILED",
            "provider_instrument_type": None,
            "observed_start": None,
            "observed_end": None,
            "candle_count": None,
            "positive_volume_day_count": None,
            "median_daily_traded_value": None,
            "measured_at": measured_at.isoformat(),
            "failure_type": "ProjectionUnavailable",
        }

    @staticmethod
    def _checkpoint_payload(
        request: EligibilityScanRequest,
        outcomes: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        return {
            "schema_version": 1,
            "request_checksum": request.checksum,
            "universe_checksum": request.universe_checksum,
            "requested_start": request.requested_start.isoformat(),
            "requested_end": request.requested_end.isoformat(),
            "outcomes": {
                key: outcomes[key]
                for key in sorted(outcomes)
            },
        }

    @classmethod
    def _outcomes(
        cls,
        value: object | None,
        request: EligibilityScanRequest,
    ) -> dict[str, dict[str, object]]:
        if value is None:
            return {}
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != 1
            or value.get("request_checksum") != request.checksum
            or value.get("universe_checksum") != request.universe_checksum
            or value.get("requested_start") != request.requested_start.isoformat()
            or value.get("requested_end") != request.requested_end.isoformat()
        ):
            raise ValueError("Checkpoint does not match eligibility request")
        raw_outcomes = value.get("outcomes")
        if not isinstance(raw_outcomes, dict):
            raise ValueError("Checkpoint outcomes are invalid")
        members = {member.key: member for member in request.members}
        outcomes: dict[str, dict[str, object]] = {}
        for key, outcome in raw_outcomes.items():
            if not isinstance(key, str) or key not in members or not isinstance(outcome, dict):
                raise ValueError("Checkpoint outcome identity is invalid")
            cls._validate_outcome(outcome, members[key])
            outcomes[key] = dict(outcome)
        return outcomes

    @staticmethod
    def _validate_outcome(
        value: dict[str, object],
        member: EligibilityMember,
    ) -> None:
        status = value.get("status")
        expected_yahoo = member.yahoo_symbol or None
        if (
            status not in _TERMINAL_STATUSES
            or value.get("source") != member.source
            or value.get("source_symbol") != member.source_symbol
            or value.get("yahoo_symbol") != expected_yahoo
        ):
            raise ValueError("Checkpoint outcome does not match universe member")
        measured_at = value.get("measured_at")
        if not isinstance(measured_at, str):
            raise ValueError("Checkpoint outcome measured_at is invalid")
        try:
            parsed = datetime.fromisoformat(measured_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Checkpoint outcome measured_at is invalid") from exc
        validate_aware_datetime(parsed, field_name="measured_at")
        if status == "SUCCESS":
            candle_count = value.get("candle_count")
            positive_count = value.get("positive_volume_day_count")
            median_value = value.get("median_daily_traded_value")
            if (
                isinstance(candle_count, bool)
                or not isinstance(candle_count, int)
                or candle_count < 1
                or isinstance(positive_count, bool)
                or not isinstance(positive_count, int)
                or not 0 <= positive_count <= candle_count
                or _finite_number(median_value, "median_daily_traded_value") < 0
            ):
                raise ValueError("Successful checkpoint metrics are invalid")
        elif status == "EMPTY":
            if value.get("candle_count") != 0 or value.get("median_daily_traded_value") is not None:
                raise ValueError("Empty checkpoint metrics are invalid")
        else:
            if not isinstance(value.get("failure_type"), str):
                raise ValueError("Failed checkpoint category is invalid")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _checksum(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _finite_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a finite number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{field_name} must be a finite number")
    return result
