"""Resumable exact-symbol Yahoo currency qualification."""

from datetime import datetime
from hashlib import sha256
import json

from investment_terminal.clients.yahoo_finance_client import (
    YahooCandleFailureCategory,
    classify_yahoo_candle_failure,
)
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class SymbolCurrencyQualificationService:
    def __init__(self, *, client, checkpoint_writer, clock) -> None:
        self.client = client
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(
        self,
        projection: object,
        projection_checksum: str,
        checkpoint: object | None = None,
        *,
        max_items: int,
    ) -> dict[str, object]:
        if isinstance(max_items, bool) or not isinstance(max_items, int):
            raise TypeError("max_items must be an integer")
        if not 1 <= max_items <= 100:
            raise ValueError("max_items must be between 1 and 100")
        symbols, actual_checksum = self._projection(projection)
        expected = normalize_required_text(
            projection_checksum, field_name="projection_checksum"
        ).lower()
        if expected != actual_checksum:
            raise ValueError("Projection checksum does not match")
        request_checksum = _checksum({
            "schema_version": 2,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
            "projection_checksum": actual_checksum,
        })
        outcomes, migrated = self._outcomes(
            checkpoint, request_checksum, actual_checksum
        )
        if migrated:
            self._write_checkpoint(request_checksum, actual_checksum, outcomes)
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        attempted = 0
        halt_category = None
        pending = [symbol for symbol in symbols if outcomes.get(symbol, {}).get("status") not in {"SUCCESS", "FINAL_FAILED"}]
        for symbol in pending[:max_items]:
            previous = outcomes.get(symbol, {})
            attempts = int(previous.get("attempt_count", 0)) + 1
            try:
                currency = self.client.get_currency(symbol)
                outcome = {"status": "SUCCESS", "attempt_count": attempts,
                           "currency": currency, "failure_category": None}
            except Exception as exc:
                category = classify_yahoo_candle_failure(exc).value
                terminal = attempts >= 3
                outcome = {"status": "FINAL_FAILED" if terminal else "RETRY_PENDING",
                           "attempt_count": attempts, "currency": None,
                           "failure_category": category}
                if category == YahooCandleFailureCategory.RATE_LIMITED.value:
                    halt_category = category
            outcomes[symbol] = outcome
            attempted += 1
            self._write_checkpoint(request_checksum, actual_checksum, outcomes)
            if halt_category is not None:
                break
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        values = list(outcomes.values())
        counts = {status: sum(item["status"] == status for item in values)
                  for status in ("SUCCESS", "FINAL_FAILED", "RETRY_PENDING")}
        terminal = counts["SUCCESS"] + counts["FINAL_FAILED"]
        return {
            "schema_version": 2,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
            "provider_identity": "YAHOO_FINANCE_CHART_METADATA",
            "status": "HALTED" if halt_category else ("COMPLETE" if terminal == len(symbols) else "IN_PROGRESS"),
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "request_checksum": request_checksum,
            "projection_checksum": actual_checksum,
            "coverage": {"member_count": len(symbols), "attempted_count": attempted,
                         "success_count": counts["SUCCESS"],
                         "final_failure_count": counts["FINAL_FAILED"],
                         "retry_pending_count": counts["RETRY_PENDING"],
                         "never_attempted_count": len(symbols) - len(outcomes)},
            "halt_category": halt_category,
            "failure_categories": sorted({item["failure_category"] for item in values
                                          if item["failure_category"]}),
            "limitations": ["report excludes symbols, currencies, paths, provider text, and exception messages",
                            "qualification does not generate batches, retrieve candles, or ingest data"],
        }

    @staticmethod
    def _projection(value: object) -> tuple[tuple[str, ...], str]:
        if not isinstance(value, dict) or value.get("schema_version") != 1 or value.get("projection_identity") != "ELIGIBILITY_SUCCESS_UNIVERSE":
            raise ValueError("Unsupported eligibility success projection")
        rows = value.get("members")
        if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Projection members are invalid")
        symbols = tuple(sorted(normalize_required_text(row.get("yahoo_symbol"), field_name="yahoo_symbol", uppercase=True) for row in rows))
        if len(set(symbols)) != len(symbols):
            raise ValueError("Projection symbols must be unique")
        return symbols, _checksum(value)

    @staticmethod
    def _exact_currencies(rows: object, symbol: str) -> tuple[tuple[str, ...], int]:
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise TypeError("Yahoo search result must contain objects")
        values = set()
        exact_count = 0
        for row in rows:
            candidate = row.get("symbol")
            if isinstance(candidate, str) and candidate.strip().upper() == symbol:
                exact_count += 1
                currency = row.get("currency")
                if isinstance(currency, str):
                    normalized = currency.strip().upper()
                    if len(normalized) == 3 and normalized.isalpha():
                        values.add(normalized)
        return tuple(sorted(values)), exact_count

    @staticmethod
    def _outcomes(
        value: object | None,
        request_checksum: str,
        projection_checksum: str,
        *,
        migrate: bool = True,
    ):
        if value is None:
            return {}, False
        if not isinstance(value, dict) or value.get("schema_version") not in {1, 2} or value.get("projection_checksum") != projection_checksum:
            raise ValueError("Checkpoint does not match request")
        if value["schema_version"] == 2 and value.get("request_checksum") != request_checksum:
            raise ValueError("Checkpoint does not match request")
        if value["schema_version"] == 1:
            legacy_checksum = _checksum({
                "schema_version": 1,
                "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
                "projection_checksum": projection_checksum,
            })
            if value.get("request_checksum") != legacy_checksum:
                raise ValueError("Checkpoint does not match request")
        outcomes = value.get("outcomes")
        if not isinstance(outcomes, dict) or any(not isinstance(key, str) or not isinstance(item, dict) for key, item in outcomes.items()):
            raise ValueError("Checkpoint outcomes are invalid")
        migrated = value["schema_version"] == 1 and migrate
        copied = {key: dict(item) for key, item in outcomes.items()}
        if migrated:
            for item in copied.values():
                if (item.get("status") == "FINAL_FAILED"
                        and item.get("failure_category") == "INVALID_CURRENCY"):
                    item["status"] = "RETRY_PENDING"
        return copied, migrated

    def _write_checkpoint(self, request_checksum, projection_checksum, outcomes):
        self.checkpoint_writer({
            "schema_version": 2,
            "request_checksum": request_checksum,
            "projection_checksum": projection_checksum,
            "outcomes": {key: dict(item) for key, item in outcomes.items()},
        })


def _checksum(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()
