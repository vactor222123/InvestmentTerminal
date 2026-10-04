"""Verify one existing private research export against its redacted report."""

from datetime import datetime, timedelta
from hashlib import sha256
import json
from math import fsum, isfinite
from numbers import Real


_COMMON_KEYS = frozenset({
    "schema_version", "manifest_checksum", "selection_checksum",
    "source_projection_sha256", "history_start", "end", "price_basis",
    "candle_count", "history_candles_sha256",
})
_PRIVATE_KEYS = _COMMON_KEYS | {
    "operation_identity", "status", "symbol", "currency", "indicator",
    "candles", "limitations",
}
_REPORT_KEYS = _COMMON_KEYS | {
    "operation_identity", "status", "sample_count_capped_at_200",
    "availability", "recent_7_calendar_day_proxy", "failure", "limitations",
}
_INDICATOR_KEYS = frozenset({
    "symbol", "currency", "weekly_status", "latest_timestamp",
    "latest_raw_close", "sample_count_capped_at_200", "sma50_raw_close",
    "sma200_raw_close", "recent_7_calendar_day_proxy", "availability",
})
_CANDLE_KEYS = frozenset({
    "timestamp", "open_price", "high_price", "low_price", "close_price",
    "volume",
})
_PRIVATE_LIMITATIONS = [
    "stored Close has no explicit Terminal-side corporate-action adjustment",
    "provider historical adjustment semantics are unverified",
    "observed rows and recency do not prove exchange-session completeness",
]
_REPORT_LIMITATIONS = [
    "report excludes instrument identity, currency, timestamps, prices and values",
    "stored Close has no explicit Terminal-side corporate-action adjustment",
    "observed rows and recency do not prove exchange-session completeness",
]


def verify_instrument_research_export(private, report, *, expected_symbol):
    """Fail closed on identity, shape, binding, or exported-candle mismatch."""
    if (not isinstance(expected_symbol, str) or not expected_symbol
            or expected_symbol != expected_symbol.strip().upper()):
        raise ValueError("Expected symbol is invalid")
    if (not isinstance(private, dict) or set(private) != _PRIVATE_KEYS
            or not isinstance(report, dict) or set(report) != _REPORT_KEYS):
        raise ValueError("Research export shape is invalid")
    if (type(private["schema_version"]) is not int
            or private["schema_version"] != 1
            or private["operation_identity"] != "INSTRUMENT_RESEARCH_EXPORT"
            or private["status"] != "COMPLETE"
            or report["operation_identity"] != "INSTRUMENT_RESEARCH_EXPORT_REPORT"
            or report["status"] != "COMPLETE"
            or report["failure"] is not None
            or private["price_basis"] != "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT"
            or private["limitations"] != _PRIVATE_LIMITATIONS
            or report["limitations"] != _REPORT_LIMITATIONS):
        raise ValueError("Research export contract is invalid")
    if any(type(private[key]) is not type(report[key])
           or private[key] != report[key] for key in _COMMON_KEYS):
        raise ValueError("Private and report bindings differ")
    for key in ("manifest_checksum", "selection_checksum",
                "source_projection_sha256", "history_candles_sha256"):
        if not _is_sha256(private[key]):
            raise ValueError("Research export checksum is invalid")
    start = _utc_midnight(private["history_start"])
    end = _utc_midnight(private["end"])
    if not start < end or end - start > timedelta(days=3660):
        raise ValueError("Research export window is invalid")
    if (private["symbol"] != expected_symbol
            or not isinstance(private["currency"], str)
            or not private["currency"]):
        raise ValueError("Research export identity is invalid")

    indicator = private["indicator"]
    if (not isinstance(indicator, dict) or set(indicator) != _INDICATOR_KEYS
            or indicator["symbol"] != expected_symbol
            or indicator["currency"] != private["currency"]
            or type(indicator["sample_count_capped_at_200"]) is not int
            or type(report["sample_count_capped_at_200"]) is not int
            or not 0 <= indicator["sample_count_capped_at_200"] <= 200
            or type(indicator["recent_7_calendar_day_proxy"]) is not bool
            or type(report["recent_7_calendar_day_proxy"]) is not bool
            or indicator["sample_count_capped_at_200"]
            != report["sample_count_capped_at_200"]
            or indicator["availability"] != report["availability"]
            or indicator["recent_7_calendar_day_proxy"]
            != report["recent_7_calendar_day_proxy"]):
        raise ValueError("Research indicator binding is invalid")

    candles = private["candles"]
    if (not isinstance(candles, list)
            or type(private["candle_count"]) is not int
            or not 0 <= len(candles) <= 4000
            or len(candles) != private["candle_count"]):
        raise ValueError("Research candle count is invalid")
    previous = None
    for candle in candles:
        if not isinstance(candle, dict) or set(candle) != _CANDLE_KEYS:
            raise ValueError("Research candle shape is invalid")
        moment = _utc_moment(candle["timestamp"])
        if (not start <= moment < end
                or previous is not None and moment <= previous):
            raise ValueError("Research candle order or window is invalid")
        prices = [candle[key] for key in (
            "open_price", "high_price", "low_price", "close_price",
        )]
        if any(not _finite_number(value, positive=True) for value in prices):
            raise ValueError("Research candle price is invalid")
        opened, high, low, closed = prices
        if high < max(opened, low, closed) or low > min(opened, high, closed):
            raise ValueError("Research candle OHLC is invalid")
        if not _finite_number(candle["volume"], positive=False):
            raise ValueError("Research candle volume is invalid")
        previous = moment
    digest = sha256(json.dumps(
        candles, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")).hexdigest()
    if digest != private["history_candles_sha256"]:
        raise ValueError("Research candle checksum mismatch")
    sample_count = indicator["sample_count_capped_at_200"]
    if len(candles) < sample_count or (sample_count == 0 and candles):
        raise ValueError("Export window omits the latest indicator sample")
    closes = [candle["close_price"] for candle in reversed(
        candles[-sample_count:] if sample_count else []
    )]
    latest = candles[-1] if sample_count else None
    availability = (
        "NO_CANDLES" if sample_count == 0 else
        "UNDER_50" if sample_count < 50 else
        "50_TO_199" if sample_count < 200 else "BOTH_AVAILABLE"
    )
    expected_indicator = {
        "latest_timestamp": latest["timestamp"] if latest else None,
        "latest_raw_close": closes[0] if closes else None,
        "sma50_raw_close": fsum(closes[:50]) / 50 if sample_count >= 50 else None,
        "sma200_raw_close": fsum(closes) / 200 if sample_count >= 200 else None,
        "recent_7_calendar_day_proxy": bool(
            latest and end - _utc_moment(latest["timestamp"]) <= timedelta(days=7)
        ),
        "availability": availability,
    }
    if any(type(indicator[key]) is not type(value)
           or indicator[key] != value for key, value in expected_indicator.items()):
        raise ValueError("Research indicator values do not match exported closes")


def _is_sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(character in "0123456789abcdef" for character in value))


def _utc_midnight(value):
    moment = _utc_moment(value)
    if moment.time() != datetime.min.time():
        raise ValueError("Research window must use UTC midnight")
    return moment


def _utc_moment(value):
    if not isinstance(value, str):
        raise ValueError("Research timestamp is invalid")
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Research timestamp is invalid") from exc
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ValueError("Research timestamp must be UTC")
    return moment


def _finite_number(value, *, positive):
    return (not isinstance(value, bool) and isinstance(value, Real)
            and isfinite(float(value)) and (value > 0 if positive else value >= 0))
