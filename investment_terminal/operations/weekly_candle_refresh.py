"""Bounded, resumable daily candle updates for successful manifest series."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
import sqlite3

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    project_yahoo_candle_failure,
)
from investment_terminal.operations.manifest_collection_sweep import (
    ManifestCollectionSweepPlan,
    _validated_checkpoint_sequence,
)
from investment_terminal.utils.validation import validate_aware_datetime


_OVERLAP = timedelta(days=7)
_MAX_WINDOW = timedelta(days=90)
_QUALITY_CATEGORIES = frozenset({
    "MISSING_STORED_HISTORY", "CURRENCY_MISMATCH", "NO_NEW_WINDOW",
    "WINDOW_TOO_LARGE", "RESPONSE_IDENTITY_OR_WINDOW", "STORED_CANDLE_DRIFT",
})
_FAILURE_CATEGORIES = _QUALITY_CATEGORIES | {
    category.value for category in YahooCandleFailureCategory
}


@dataclass(frozen=True, slots=True)
class WeeklyCandleRefreshPlan:
    manifest_checksum: str
    end: datetime
    items: tuple[tuple[str, str], ...]
    excluded_count: int
    selection_checksum: str

    @classmethod
    def from_manifest(cls, manifest, manifest_checksum, checkpoint_reader, *, end):
        validated_end = validate_aware_datetime(end, field_name="end")
        if validated_end.utcoffset() != timedelta(0):
            raise ValueError("end must be in UTC")
        if validated_end.time() != datetime.min.time():
            raise ValueError("end must be a UTC midnight boundary")
        source = ManifestCollectionSweepPlan.from_manifest(
            manifest, manifest_checksum, max_batches=1
        )
        _, states, first_unswept = _validated_checkpoint_sequence(
            source, checkpoint_reader
        )
        if first_unswept <= len(source.requests):
            raise ValueError("Complete source checkpoint coverage is required")
        if any(request.resolution != "D" for request in source.requests):
            raise ValueError("Weekly refresh requires daily source requests")
        items = []
        excluded = 0
        for request, state in zip(source.requests, states, strict=True):
            for item in request.items:
                outcome = state.outcomes[item.symbol]
                if outcome["status"] == "SUCCESS":
                    items.append((item.symbol, item.currency))
                else:
                    excluded += 1
        if not items or len({symbol for symbol, _ in items}) != len(items):
            raise ValueError("Source success identities are empty or duplicated")
        encoded = json.dumps(items, separators=(",", ":"), ensure_ascii=True)
        return cls(
            source.manifest_checksum,
            validated_end,
            tuple(items),
            excluded,
            sha256(encoded.encode("ascii")).hexdigest(),
        )


def _validated_outcomes(checkpoint, plan):
    if checkpoint is None:
        return {}
    if not isinstance(checkpoint, dict) or set(checkpoint) != {
        "schema_version", "operation_identity", "manifest_checksum", "end",
        "selection_checksum", "outcomes",
    }:
        raise ValueError("Weekly checkpoint shape is invalid")
    if (
        checkpoint["schema_version"] != 1
        or checkpoint["operation_identity"] != "WEEKLY_CANDLE_REFRESH"
        or checkpoint["manifest_checksum"] != plan.manifest_checksum
        or checkpoint["end"] != plan.end.isoformat()
        or checkpoint["selection_checksum"] != plan.selection_checksum
    ):
        raise ValueError("Weekly checkpoint binding is invalid")
    outcomes = checkpoint["outcomes"]
    if not isinstance(outcomes, dict) or not set(outcomes).issubset(
        {symbol for symbol, _ in plan.items}
    ):
        raise ValueError("Weekly checkpoint outcomes are invalid")
    for value in outcomes.values():
        if not isinstance(value, dict) or set(value) != {
            "status", "category", "downloaded", "inserted", "duplicates",
            "omitted_trailing_count", "stored_count",
        }:
            raise ValueError("Weekly checkpoint outcome shape is invalid")
        if value["status"] not in {"SUCCESS", "EMPTY", "FAILED"}:
            raise ValueError("Weekly checkpoint status is invalid")
        if value["category"] is not None and (
            not isinstance(value["category"], str)
            or value["category"] not in _FAILURE_CATEGORIES
        ):
            raise ValueError("Weekly checkpoint category is invalid")
        for field in (
            "downloaded", "inserted", "duplicates", "omitted_trailing_count",
            "stored_count",
        ):
            count = value[field]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("Weekly checkpoint count is invalid")
        if value["status"] == "FAILED":
            if value["category"] is None or any(
                value[field] for field in (
                    "downloaded", "inserted", "duplicates",
                    "omitted_trailing_count", "stored_count",
                )
            ):
                raise ValueError("Weekly failed outcome is invalid")
        elif value["category"] is not None or value["omitted_trailing_count"] > 1 or value["downloaded"] != (
            value["inserted"] + value["duplicates"]
        ) or (value["status"] == "EMPTY" and value["downloaded"] != 0):
            raise ValueError("Weekly completed outcome is invalid")
    return dict(outcomes)


class WeeklyCandleRefreshService:
    """Update only previously successful daily series, one SQLite commit each."""

    def __init__(self, *, client, repository, checkpoint_writer, clock):
        self.client = client
        self.repository = repository
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(self, plan, checkpoint=None, *, max_items):
        if not isinstance(plan, WeeklyCandleRefreshPlan):
            raise TypeError("plan must be a WeeklyCandleRefreshPlan")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or not (
            1 <= max_items <= len(plan.items)
        ):
            raise ValueError("max_items is outside the selected series")
        outcomes = _validated_outcomes(checkpoint, plan)
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        if plan.end > started.astimezone(plan.end.tzinfo).replace(
            hour=0, minute=0, second=0, microsecond=0
        ):
            raise ValueError("end cannot be after the last completed UTC day")
        attempted = 0
        halted = False
        for symbol, currency in plan.items:
            if symbol in outcomes:
                continue
            if attempted >= max_items:
                break
            attempted += 1
            result = self._refresh_one(symbol, currency, plan.end)
            outcomes[symbol] = result
            self.checkpoint_writer({
                "schema_version": 1,
                "operation_identity": "WEEKLY_CANDLE_REFRESH",
                "manifest_checksum": plan.manifest_checksum,
                "end": plan.end.isoformat(),
                "selection_checksum": plan.selection_checksum,
                "outcomes": dict(outcomes),
            })
            if result["category"] == "RATE_LIMITED":
                halted = True
                break
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        if completed < started:
            raise ValueError("completed_at is before started_at")
        counts = Counter(value["status"] for value in outcomes.values())
        categories = Counter(
            value["category"] for value in outcomes.values()
            if value["status"] == "FAILED"
        )
        remaining = len(plan.items) - len(outcomes)
        status = (
            "HALTED" if halted else "BUDGET_EXHAUSTED" if remaining
            else "COMPLETE_WITH_FAILURES" if counts["FAILED"] else "COMPLETE"
        )
        return {
            "schema_version": 1,
            "operation_identity": "WEEKLY_CANDLE_REFRESH",
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "manifest_checksum": plan.manifest_checksum,
            "end": plan.end.isoformat(),
            "selection_checksum": plan.selection_checksum,
            "budget": {"max_items": max_items},
            "coverage": {
                "selected_count": len(plan.items),
                "source_excluded_count": plan.excluded_count,
                "completed_count": len(outcomes),
                "remaining_count": remaining,
                "success_count": counts["SUCCESS"],
                "empty_count": counts["EMPTY"],
                "failure_count": counts["FAILED"],
                "indicator_200_ready_count": sum(
                    value["status"] != "FAILED" and value["stored_count"] >= 200
                    for value in outcomes.values()
                ),
                "current_run_attempted_count": attempted,
                "downloaded_total": sum(x["downloaded"] for x in outcomes.values()),
                "inserted_total": sum(x["inserted"] for x in outcomes.values()),
                "duplicate_total": sum(x["duplicates"] for x in outcomes.values()),
                "omitted_trailing_total": sum(
                    x["omitted_trailing_count"] for x in outcomes.values()
                ),
            },
            "failure_categories": [
                {"category": category, "count": count}
                for category, count in sorted(categories.items())
            ],
            "failure": None,
            "limitations": [
                "indicator_200_ready_count proves stored sample size only, not session completeness or freshness",
                "report excludes identities, currencies, prices, paths, provider text, and exception messages",
            ],
        }

    def _refresh_one(self, symbol, currency, end):
        try:
            latest = self.repository.get_latest(symbol, "D")
            if latest is None:
                raise _SeriesQualityError("MISSING_STORED_HISTORY")
            if latest.currency != currency:
                raise _SeriesQualityError("CURRENCY_MISMATCH")
            start = latest.timestamp - _OVERLAP
            if start >= end:
                raise _SeriesQualityError("NO_NEW_WINDOW")
            if end - start > _MAX_WINDOW:
                raise _SeriesQualityError("WINDOW_TOO_LARGE")
            existing = {
                candle.timestamp: candle
                for candle in self.repository.get_range(symbol, "D", start, end)
            }
            projection = self.client.get_candle_projection(
                symbol=symbol, resolution="D", start=start, end=end,
                currency=currency, allow_trailing_incomplete=True,
            )
            candles = list(projection.candles)
            for candle in candles:
                if (
                    candle.symbol != symbol or candle.resolution != "D"
                    or candle.currency != currency or not start <= candle.timestamp < end
                ):
                    raise _SeriesQualityError("RESPONSE_IDENTITY_OR_WINDOW")
                previous = existing.get(candle.timestamp)
                if previous is not None and any(
                    getattr(previous, field) != getattr(candle, field)
                    for field in (
                        "open_price", "high_price", "low_price", "close_price", "volume", "currency"
                    )
                ):
                    raise _SeriesQualityError("STORED_CANDLE_DRIFT")
            try:
                inserted = self.repository.save_many(candles)
                stored_count = self.repository.count(symbol, "D")
            except Exception as exc:
                raise _PersistenceError("Candle persistence failed") from exc
            if not 0 <= inserted <= len(candles):
                raise _PersistenceError("Invalid inserted count")
            return {
                "status": "SUCCESS" if candles else "EMPTY",
                "category": None,
                "downloaded": len(candles),
                "inserted": inserted,
                "duplicates": len(candles) - inserted,
                "omitted_trailing_count": projection.omitted_trailing_count,
                "stored_count": stored_count,
            }
        except _SeriesQualityError as exc:
            category = exc.category
        except (sqlite3.Error, _PersistenceError):
            raise
        except Exception as exc:
            category = project_yahoo_candle_failure(exc).category.value
        return {
            "status": "FAILED", "category": category,
            "downloaded": 0, "inserted": 0, "duplicates": 0,
            "omitted_trailing_count": 0, "stored_count": 0,
        }


class _SeriesQualityError(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


class _PersistenceError(Exception):
    """Unexpected repository contract failure must stop the run."""
