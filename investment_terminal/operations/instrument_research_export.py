"""Read-only, single-instrument factual export from a bound SMA projection."""

from datetime import datetime, timedelta
from hashlib import sha256
import json
from math import fsum, isfinite
from numbers import Real

from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    _validated_outcomes,
)


_MAX_WINDOW = timedelta(days=3660)
_MAX_CANDLES = 4000
_PRICE_BASIS = "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT"
_ITEM_KEYS = frozenset({
    "symbol", "currency", "weekly_status", "latest_timestamp",
    "latest_raw_close", "sample_count_capped_at_200", "sma50_raw_close",
    "sma200_raw_close", "recent_7_calendar_day_proxy", "availability",
})


def build_instrument_research_export(
    plan, checkpoint, projection, projection_checksum, connection,
    *, symbol, history_start,
):
    """Return a private bounded history and a separate redacted report."""
    if not isinstance(plan, WeeklyCandleRefreshPlan):
        raise TypeError("plan must be a WeeklyCandleRefreshPlan")
    if (not isinstance(symbol, str) or not symbol.strip()
            or symbol != symbol.strip().upper()):
        raise ValueError("symbol must be a canonical selected symbol")
    if (not isinstance(history_start, datetime) or history_start.tzinfo is None
            or history_start.utcoffset() != timedelta(0)
            or history_start.time() != datetime.min.time()
            or not history_start < plan.end
            or plan.end - history_start > _MAX_WINDOW):
        raise ValueError("history_start must define a bounded UTC window")
    if (not isinstance(projection_checksum, str)
            or len(projection_checksum) != 64
            or any(character not in "0123456789abcdef" for character in projection_checksum)):
        raise ValueError("projection checksum is invalid")
    outcomes = _validated_outcomes(checkpoint, plan)
    if len(outcomes) != len(plan.items):
        raise ValueError("Complete weekly checkpoint coverage is required")
    if not isinstance(projection, dict) or set(projection) != {
        "schema_version", "manifest_checksum", "selection_checksum", "end",
        "price_basis", "selected_series_count", "processed_count",
        "max_items", "operation_identity", "status", "items", "limitations",
    }:
        raise ValueError("Private projection shape is invalid")
    binding = {
        "schema_version": 1,
        "manifest_checksum": plan.manifest_checksum,
        "selection_checksum": plan.selection_checksum,
        "end": plan.end.isoformat(),
        "price_basis": _PRICE_BASIS,
        "selected_series_count": len(plan.items),
        "processed_count": len(plan.items),
        "max_items": len(plan.items),
        "operation_identity": "LATEST_RAW_INDICATOR_PROJECTION",
        "status": "COMPLETE",
    }
    if any(type(projection.get(key)) is not type(value)
           or projection.get(key) != value for key, value in binding.items()):
        raise ValueError("Private projection binding is invalid")
    items = projection["items"]
    if not isinstance(items, list) or len(items) != len(plan.items):
        raise ValueError("Private projection selection is incomplete")
    selected = None
    for item, (expected_symbol, expected_currency) in zip(
        items, plan.items, strict=True,
    ):
        if (not isinstance(item, dict) or set(item) != _ITEM_KEYS
                or item.get("symbol") != expected_symbol
                or item.get("currency") != expected_currency
                or item.get("weekly_status") != outcomes[expected_symbol]["status"]):
            raise ValueError("Private projection selection is invalid")
        if expected_symbol == symbol:
            selected = item
    if selected is None:
        raise ValueError("Symbol is not in the selected series")
    currency = selected["currency"]
    if connection.execute(
        """SELECT 1 FROM candles WHERE symbol = ? AND resolution = 'D'
           AND (julianday(timestamp) IS NULL OR currency != ?) LIMIT 1""",
        (symbol, currency),
    ).fetchone() is not None:
        raise ValueError("Selected stored series has invalid timestamp or currency")

    end_jd = connection.execute(
        "SELECT julianday(?)", (plan.end.isoformat(),)
    ).fetchone()[0]
    start_jd = connection.execute(
        "SELECT julianday(?)", (history_start.isoformat(),)
    ).fetchone()[0]
    if start_jd is None or end_jd is None:
        raise ValueError("Invalid history window")
    latest = connection.execute(
        """SELECT timestamp, close_price FROM candles
           WHERE symbol = ? AND resolution = 'D' AND julianday(timestamp) < ?
           ORDER BY timestamp DESC LIMIT 200""",
        (symbol, end_jd),
    ).fetchall()
    closes = []
    latest_timestamps = []
    for timestamp, close in latest:
        moment = _utc_moment(timestamp)
        if moment >= plan.end or (latest_timestamps and moment >= latest_timestamps[-1]):
            raise ValueError("Selected stored series has invalid timestamp order")
        closes.append(_finite_positive(close, "close_price"))
        latest_timestamps.append(moment)
    count = len(closes)
    availability = (
        "NO_CANDLES" if count == 0 else "UNDER_50" if count < 50
        else "50_TO_199" if count < 200 else "BOTH_AVAILABLE"
    )
    expected = {
        "latest_timestamp": latest_timestamps[0].isoformat() if count else None,
        "latest_raw_close": closes[0] if count else None,
        "sample_count_capped_at_200": count,
        "sma50_raw_close": fsum(closes[:50]) / 50 if count >= 50 else None,
        "sma200_raw_close": fsum(closes) / 200 if count >= 200 else None,
        "recent_7_calendar_day_proxy": bool(
            count and plan.end - latest_timestamps[0] <= timedelta(days=7)
        ),
        "availability": availability,
    }
    if any(type(selected.get(key)) is not type(value)
           or selected.get(key) != value for key, value in expected.items()):
        raise ValueError("Private projection no longer matches stored closes")

    rows = connection.execute(
        """SELECT timestamp, open_price, high_price, low_price, close_price,
                  volume, currency FROM candles
           WHERE symbol = ? AND resolution = 'D'
             AND julianday(timestamp) >= ? AND julianday(timestamp) < ?
           ORDER BY timestamp ASC LIMIT ?""",
        (symbol, start_jd, end_jd, _MAX_CANDLES + 1),
    ).fetchall()
    if len(rows) > _MAX_CANDLES:
        raise ValueError("Selected history exceeds the candle bound")
    candles = []
    previous = None
    for timestamp, open_price, high_price, low_price, close_price, volume, row_currency in rows:
        moment = _utc_moment(timestamp)
        if (not history_start <= moment < plan.end
                or previous is not None and moment <= previous
                or row_currency != currency):
            raise ValueError("Selected history identity or order is invalid")
        prices = {
            "open_price": _finite_positive(open_price, "open_price"),
            "high_price": _finite_positive(high_price, "high_price"),
            "low_price": _finite_positive(low_price, "low_price"),
            "close_price": _finite_positive(close_price, "close_price"),
        }
        if (prices["high_price"] < max(prices["open_price"], prices["low_price"], prices["close_price"])
                or prices["low_price"] > min(prices["open_price"], prices["high_price"], prices["close_price"])):
            raise ValueError("Selected history has invalid OHLC")
        if (isinstance(volume, bool) or not isinstance(volume, Real)
                or not isfinite(float(volume)) or volume < 0):
            raise ValueError("Selected history has invalid volume")
        candles.append({"timestamp": moment.isoformat(), **prices, "volume": float(volume)})
        previous = moment

    common = {
        "schema_version": 1,
        "manifest_checksum": plan.manifest_checksum,
        "selection_checksum": plan.selection_checksum,
        "source_projection_sha256": projection_checksum,
        "history_start": history_start.isoformat(),
        "end": plan.end.isoformat(),
        "price_basis": _PRICE_BASIS,
        "candle_count": len(candles),
        "history_candles_sha256": sha256(json.dumps(
            candles, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("ascii")).hexdigest(),
    }
    private = {
        **common,
        "operation_identity": "INSTRUMENT_RESEARCH_EXPORT",
        "status": "COMPLETE",
        "symbol": symbol,
        "currency": currency,
        "indicator": dict(selected),
        "candles": candles,
        "limitations": [
            "stored Close has no explicit Terminal-side corporate-action adjustment",
            "provider historical adjustment semantics are unverified",
            "observed rows and recency do not prove exchange-session completeness",
        ],
    }
    report = {
        **common,
        "operation_identity": "INSTRUMENT_RESEARCH_EXPORT_REPORT",
        "status": "COMPLETE",
        "sample_count_capped_at_200": count,
        "availability": availability,
        "recent_7_calendar_day_proxy": expected["recent_7_calendar_day_proxy"],
        "failure": None,
        "limitations": [
            "report excludes instrument identity, currency, timestamps, prices and values",
            "stored Close has no explicit Terminal-side corporate-action adjustment",
            "observed rows and recency do not prove exchange-session completeness",
        ],
    }
    return private, report


def _utc_moment(value):
    if not isinstance(value, str):
        raise ValueError("Stored timestamp is invalid")
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Stored timestamp is invalid") from exc
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ValueError("Stored timestamp is not UTC")
    return moment


def _finite_positive(value, field):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(float(value)) or value <= 0):
        raise ValueError(f"Selected history has invalid {field}")
    return float(value)
