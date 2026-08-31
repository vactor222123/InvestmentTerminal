"""Privacy-safe diagnosis of one failed Yahoo eligibility candle series."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from numbers import Real

import pandas as pd

from investment_terminal.operations.universe_eligibility_scan import (
    EligibilityScanRequest,
    UniverseEligibilityScanService,
)
from investment_terminal.utils.validation import validate_aware_datetime


_PRICE_COLUMNS = ("Open", "High", "Low", "Close")
_REQUIRED_COLUMNS = (*_PRICE_COLUMNS, "Volume")


class SingleSeriesCandleDiagnosticService:
    """Select and inspect one RESPONSE_NUMERIC series without mutating state."""

    def __init__(self, *, client, clock) -> None:
        self.client = client
        self.clock = clock

    def run(self, request: EligibilityScanRequest, checkpoint: object) -> dict[str, object]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        if not isinstance(checkpoint, dict) or checkpoint.get("schema_version") != 3:
            raise ValueError("A schema-version-3 eligibility checkpoint is required")
        outcomes, migrated_count = UniverseEligibilityScanService._outcomes(
            checkpoint,
            request,
            migrate=False,
        )
        if migrated_count:
            raise ValueError("Diagnostic must not migrate checkpoint evidence")
        members = {member.key: member for member in request.members}
        candidate_keys = sorted(
            key
            for key, outcome in outcomes.items()
            if outcome.get("status") == "FINAL_FAILED"
            and outcome.get("failure_category") == "RESPONSE_NUMERIC"
        )
        if not candidate_keys:
            raise ValueError("Checkpoint contains no RESPONSE_NUMERIC candidate")
        selected = members[candidate_keys[0]]
        frame = self.client.get_daily_frame(
            symbol=selected.yahoo_symbol,
            start=request.requested_start,
            end=request.requested_end,
        )
        analysis = _analyze_frame(frame)
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE",
            "diagnostic_identity": "SINGLE_SERIES_RAW_CANDLE_DIAGNOSTIC",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "request_checksum": request.checksum,
            "universe_checksum": request.universe_checksum,
            "requested_start": request.requested_start.isoformat(),
            "requested_end": request.requested_end.isoformat(),
            "selection": {
                "failure_category": "RESPONSE_NUMERIC",
                "eligible_candidate_count": len(candidate_keys),
                "selected_count": 1,
            },
            "coverage": analysis,
            "failure": None,
            "limitations": [
                "report excludes symbols, names, prices, paths, provider text, and exception messages",
                "one raw series diagnostic does not change eligibility evidence or authorize ingestion",
            ],
        }


def _analyze_frame(frame: object) -> dict[str, object]:
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("Raw candle diagnostic frame is invalid")
    missing = sorted(set(_REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError("Raw candle diagnostic frame is missing required columns")
    reason_counts: dict[str, int] = {}
    invalid_rows: list[dict[str, object]] = []
    valid_count = 0
    for index, row in frame.iterrows():
        reasons: list[str] = []
        values: dict[str, float] = {}
        for column in _PRICE_COLUMNS:
            reason, numeric = _numeric_reason(row[column], positive=True)
            if reason:
                reasons.append(f"{column.upper()}_{reason}")
            elif numeric is not None:
                values[column] = numeric
        reason, numeric = _numeric_reason(row["Volume"], positive=False)
        if reason:
            reasons.append(f"VOLUME_{reason}")
        elif numeric is not None:
            values["Volume"] = numeric
        if len(values) == len(_REQUIRED_COLUMNS):
            if values["High"] < max(values["Open"], values["Low"], values["Close"]):
                reasons.append("HIGH_INCONSISTENT")
            if values["Low"] > min(values["Open"], values["High"], values["Close"]):
                reasons.append("LOW_INCONSISTENT")
        if reasons:
            unique_reasons = sorted(set(reasons))
            for item in unique_reasons:
                reason_counts[item] = reason_counts.get(item, 0) + 1
            invalid_rows.append({
                "observed_at": _redacted_timestamp(index),
                "reasons": unique_reasons,
            })
        else:
            valid_count += 1
    return {
        "raw_row_count": len(frame),
        "valid_row_count": valid_count,
        "invalid_row_count": len(invalid_rows),
        "invalid_reason_counts": {
            key: reason_counts[key] for key in sorted(reason_counts)
        },
        "invalid_rows": invalid_rows,
    }


def _numeric_reason(value: object, *, positive: bool) -> tuple[str | None, float | None]:
    if isinstance(value, bool) or not isinstance(value, Real):
        return "NOT_REAL", None
    numeric = float(value)
    if not isfinite(numeric):
        return "NON_FINITE", None
    if positive and numeric <= 0:
        return "NON_POSITIVE", None
    if not positive and numeric < 0:
        return "NEGATIVE", None
    return None, numeric


def _redacted_timestamp(value: object) -> str | None:
    if isinstance(value, pd.Timestamp):
        parsed = value.to_pydatetime()
    elif isinstance(value, datetime):
        parsed = value
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()
