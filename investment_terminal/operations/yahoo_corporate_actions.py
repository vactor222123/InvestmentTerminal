"""Validate and retain action observations separately from OHLCV and ledgers."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from investment_terminal.market.corporate_actions import (
    ACTION_KINDS, MAX_ROWS, CorporateAction, CorporateActionSnapshot, LIMITATIONS,
)
from investment_terminal.operations.yahoo_price_basis_qualification import PriceBasisRequest
from investment_terminal.utils.validation import validate_finite_number


class ActionValidationError(ValueError):
    """A fixed privacy-safe category, never a provider message."""


def build_snapshot(request: PriceBasisRequest, frame, metadata, *, fetched_at,
                   adapter_version) -> CorporateActionSnapshot:
    if not isinstance(request, PriceBasisRequest):
        raise TypeError("request must be PriceBasisRequest")
    if not isinstance(metadata, dict):
        raise ActionValidationError("METADATA")
    if metadata.get("symbol") != request.symbol:
        raise ActionValidationError("SYMBOL_MISMATCH")
    try:
        zone = ZoneInfo(metadata["exchangeTimezoneName"])
    except (KeyError, TypeError, ValueError):
        raise ActionValidationError("TIMEZONE") from None
    if not isinstance(frame, pd.DataFrame):
        raise ActionValidationError("FRAME_TYPE")
    if len(frame.index) == 0:
        raise ActionValidationError("EMPTY_HISTORY")
    if len(frame.index) > MAX_ROWS:
        raise ActionValidationError("ROW_LIMIT")
    if (not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None
            or frame.index.hasnans or not frame.index.is_unique
            or not frame.index.is_monotonic_increasing):
        raise ActionValidationError("TIMESTAMP_INDEX")
    index = frame.index.tz_convert(timezone.utc)
    if index[0] < request.start or index[-1] >= request.end:
        raise ActionValidationError("TIMESTAMP_WINDOW")
    dates = frame.index.tz_convert(zone).date
    if len(set(dates)) != len(dates):
        raise ActionValidationError("DUPLICATE_SESSION_DATE")
    if (not frame.columns.is_unique
            or not all(isinstance(column, str) for column in frame.columns)):
        raise ActionValidationError("COLUMN_SHAPE")
    if not {"Dividends", "Stock Splits"}.issubset(frame.columns):
        raise ActionValidationError("MISSING_ACTION_FIELDS")
    events = []
    for column, kind in (("Capital Gains", "CAPITAL_GAIN"),
                         ("Dividends", "DIVIDEND"), ("Stock Splits", "SPLIT")):
        if column not in frame:
            continue  # Absence is explicitly recorded, never manufactured zeros.
        for position, raw in enumerate(frame[column]):
            try:
                value = validate_finite_number(raw, field_name="action")
                if value < 0 or kind == "SPLIT" and value == 1:
                    raise ValueError("Invalid action")
            except (TypeError, ValueError, OverflowError):
                raise ActionValidationError("ACTION_VALUE") from None
            if value:
                events.append(CorporateAction(
                    index[position].to_pydatetime(), dates[position].isoformat(),
                    kind, value,
                ))
    try:
        return CorporateActionSnapshot(
            symbol=request.symbol, start=request.start, end=request.end,
            fetched_at=fetched_at, adapter_version=adapter_version,
            quote_currency=metadata.get("currency"),
            exchange_timezone=metadata["exchangeTimezoneName"],
            instrument_type=metadata.get("instrumentType"),
            row_count=len(frame), first_row_at=index[0].to_pydatetime(),
            last_row_at=index[-1].to_pydatetime(),
            capital_gains_present="Capital Gains" in frame,
            events=tuple(sorted(events, key=lambda item: (item.timestamp, item.kind))),
        )
    except (TypeError, ValueError):
        raise ActionValidationError("SNAPSHOT_METADATA") from None


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def load_snapshot(path: Path):
    with path.open("rb") as source:
        data = source.read(4_000_001)
    if len(data) > 4_000_000:
        raise ValueError("Snapshot exceeds byte bound")
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    return CorporateActionSnapshot.from_dict(value), sha256(data).hexdigest()


def build_report(snapshot=None, *, file_sha256=None, reused=False,
                 failure_category=None, snapshot_persisted=False):
    counts = None if snapshot is None else {
        kind: sum(event.kind == kind for event in snapshot.events)
        for kind in ACTION_KINDS
    }
    return {
        "schema_version": 1,
        "operation_identity": "YAHOO_CORPORATE_ACTION_COLLECTION",
        "status": "FAILED" if failure_category else "STORED",
        "observed_layer": "YFINANCE_HISTORY_FRAME",
        "snapshot_persisted": snapshot_persisted,
        "reused_snapshot": reused,
        "snapshot_sha256": file_sha256,
        "content_sha256": snapshot.to_dict()["content_sha256"] if snapshot else None,
        "row_count": snapshot.row_count if snapshot else None,
        "event_counts": counts,
        "capital_gains_field_present": snapshot.capital_gains_present if snapshot else None,
        "raw_source_presence": "UNKNOWN",
        "action_completeness": "UNKNOWN",
        "failure_category": failure_category,
        "limitations": list(LIMITATIONS),
    }
