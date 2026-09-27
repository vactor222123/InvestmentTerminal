"""Offline aggregate measurement of checkpointed weekly daily series."""

from collections import Counter

from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    _validated_outcomes,
)


def measure_weekly_stored_coverage(plan, checkpoint, connection):
    """Measure SQLite rows before the bound exclusive end, without identities."""
    if not isinstance(plan, WeeklyCandleRefreshPlan):
        raise TypeError("plan must be a WeeklyCandleRefreshPlan")
    outcomes = _validated_outcomes(checkpoint, plan)
    if len(outcomes) != len(plan.items):
        raise ValueError("Complete weekly checkpoint coverage is required")

    end_jd = connection.execute(
        "SELECT julianday(?)", (plan.end.isoformat(),)
    ).fetchone()[0]
    if end_jd is None:
        raise ValueError("Invalid end boundary")
    bins = Counter()
    status_bins = Counter()
    failure_categories = Counter()
    row_total = 0
    recent_count = 0
    future_row_count = 0
    for symbol, currency in plan.items:
        total, before_end, last_jd, invalid, mismatched = connection.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(julianday(timestamp) < ?), 0),
                      MAX(CASE WHEN julianday(timestamp) < ? THEN julianday(timestamp) END),
                      COALESCE(SUM(julianday(timestamp) IS NULL), 0),
                      COALESCE(SUM(julianday(timestamp) < ? AND currency != ?), 0)
               FROM candles WHERE symbol = ? AND resolution = 'D'""",
            (end_jd, end_jd, end_jd, currency, symbol),
        ).fetchone()
        if invalid or mismatched:
            raise ValueError("Selected stored series has invalid timestamps or currency")
        count = int(before_end)
        row_total += count
        future_row_count += total - count
        if count == 0:
            bucket = "zero"
        elif count < 50:
            bucket = "one_to_49"
        elif count < 200:
            bucket = "50_to_199"
        else:
            bucket = "200_plus"
        bins[bucket] += 1
        status = outcomes[symbol]["status"]
        status_bins[status] += 1
        if status == "FAILED":
            failure_categories[outcomes[symbol]["category"]] += 1
        if last_jd is not None and end_jd - last_jd <= 7:
            recent_count += 1

    selected = len(plan.items)
    return {
        "schema_version": 1,
        "operation_identity": "WEEKLY_STORED_COVERAGE",
        "status": "COMPLETE",
        "manifest_checksum": plan.manifest_checksum,
        "selection_checksum": plan.selection_checksum,
        "end": plan.end.isoformat(),
        "coverage": {
            "selected_series_count": selected,
            "source_excluded_count": plan.excluded_count,
            "stored_row_count_before_end": row_total,
            "row_count_at_or_after_end": future_row_count,
            "zero_count": bins["zero"],
            "one_to_49_count": bins["one_to_49"],
            "50_to_199_count": bins["50_to_199"],
            "200_plus_count": bins["200_plus"],
            "sample_50_ready_count": bins["50_to_199"] + bins["200_plus"],
            "sample_200_ready_count": bins["200_plus"],
            "last_candle_within_7_calendar_days_count": recent_count,
            "weekly_success_count": status_bins["SUCCESS"],
            "weekly_empty_count": status_bins["EMPTY"],
            "weekly_failure_count": status_bins["FAILED"],
        },
        "weekly_failure_categories": [
            {"category": category, "count": count}
            for category, count in sorted(failure_categories.items())
        ],
        "failure": None,
        "limitations": [
            "sample readiness proves row count only, not calendar completeness or valid indicators",
            "seven-calendar-day recency is a proxy, not exchange-session freshness",
            "report excludes identities, currencies, prices, paths, and per-series timestamps",
        ],
    }
