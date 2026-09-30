"""Bounded, read-only latest SMA projection from stored raw daily closes."""

from collections import Counter
from datetime import datetime, timedelta
from math import fsum, isfinite
from numbers import Real

from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    _validated_outcomes,
)


def project_latest_raw_indicators(plan, checkpoint, connection, *, max_items):
    """Return private values and a separate redacted aggregate report."""
    if not isinstance(plan, WeeklyCandleRefreshPlan):
        raise TypeError("plan must be a WeeklyCandleRefreshPlan")
    if (isinstance(max_items, bool) or not isinstance(max_items, int)
            or not 1 <= max_items <= len(plan.items)):
        raise ValueError("max_items is outside the selected series")
    outcomes = _validated_outcomes(checkpoint, plan)
    if len(outcomes) != len(plan.items):
        raise ValueError("Complete weekly checkpoint coverage is required")
    end_jd = connection.execute(
        "SELECT julianday(?)", (plan.end.isoformat(),)
    ).fetchone()[0]
    if end_jd is None:
        raise ValueError("Invalid end boundary")

    items = []
    counts = Counter()
    for symbol, currency in plan.items[:max_items]:
        if connection.execute(
            """SELECT 1 FROM candles WHERE symbol = ? AND resolution = 'D'
               AND (julianday(timestamp) IS NULL OR currency != ?) LIMIT 1""",
            (symbol, currency),
        ).fetchone() is not None:
            raise ValueError("Selected stored series has invalid timestamps or currency")
        rows = connection.execute(
            """SELECT timestamp, close_price FROM candles
               WHERE symbol = ? AND resolution = 'D'
                 AND julianday(timestamp) < ?
               ORDER BY timestamp DESC LIMIT 200""",
            (symbol, end_jd),
        ).fetchall()
        closes = []
        timestamps = []
        for timestamp, close in rows:
            moment = datetime.fromisoformat(timestamp)
            if (moment.tzinfo is None or moment.utcoffset() != timedelta(0)
                    or moment >= plan.end or (timestamps and moment >= timestamps[-1])):
                raise ValueError("Selected stored series has invalid timestamp order")
            if (isinstance(close, bool) or not isinstance(close, Real)
                    or not isfinite(float(close)) or close <= 0):
                raise ValueError("Selected stored series has invalid close price")
            timestamps.append(moment)
            closes.append(float(close))
        count = len(closes)
        availability = (
            "NO_CANDLES" if count == 0 else
            "UNDER_50" if count < 50 else
            "50_TO_199" if count < 200 else "BOTH_AVAILABLE"
        )
        recent = bool(timestamps and plan.end - timestamps[0] <= timedelta(days=7))
        counts[availability] += 1
        counts["recent_7_day_proxy"] += recent
        counts["sma50_available"] += count >= 50
        counts["sma200_available"] += count >= 200
        items.append({
            "symbol": symbol,
            "currency": currency,
            "weekly_status": outcomes[symbol]["status"],
            "latest_timestamp": timestamps[0].isoformat() if timestamps else None,
            "latest_raw_close": closes[0] if closes else None,
            "sample_count_capped_at_200": count,
            "sma50_raw_close": fsum(closes[:50]) / 50 if count >= 50 else None,
            "sma200_raw_close": fsum(closes) / 200 if count >= 200 else None,
            "recent_7_calendar_day_proxy": recent,
            "availability": availability,
        })

    binding = {
        "schema_version": 1,
        "manifest_checksum": plan.manifest_checksum,
        "selection_checksum": plan.selection_checksum,
        "end": plan.end.isoformat(),
        "price_basis": "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT",
        "selected_series_count": len(plan.items),
        "processed_count": len(items),
        "max_items": max_items,
    }
    private = {
        **binding,
        "operation_identity": "LATEST_RAW_INDICATOR_PROJECTION",
        "status": "COMPLETE",
        "items": items,
        "limitations": [
            "Terminal applies no corporate-action adjustment to stored Close",
            "provider historical adjustment semantics are not verified",
            "sample counts and seven-day recency do not prove session completeness",
        ],
    }
    report = {
        **binding,
        "operation_identity": "LATEST_RAW_INDICATOR_PROJECTION_REPORT",
        "status": "COMPLETE",
        "availability_counts": [
            {"category": key, "count": counts[key]}
            for key in ("NO_CANDLES", "UNDER_50", "50_TO_199", "BOTH_AVAILABLE")
        ],
        "sma50_available_count": counts["sma50_available"],
        "sma200_available_count": counts["sma200_available"],
        "recent_7_calendar_day_proxy_count": counts["recent_7_day_proxy"],
        "failure": None,
        "limitations": [
            "report excludes identities, currencies, timestamps, prices and SMA values",
            "Terminal applies no corporate-action adjustment to stored Close",
            "provider historical adjustment semantics are not verified",
            "SMA values are not a trading recommendation",
            "sample counts and seven-day recency do not prove session completeness",
        ],
    }
    return private, report
