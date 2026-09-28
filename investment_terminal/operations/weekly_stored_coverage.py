"""Offline aggregate measurement of checkpointed weekly daily series."""

from collections import Counter
from datetime import datetime, timedelta

from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    _validated_outcomes,
)
from investment_terminal.utils.validation import validate_aware_datetime


def measure_weekly_stored_coverage(plan, checkpoint, connection, *, history_start=None):
    """Measure SQLite rows before the bound exclusive end, without identities."""
    if not isinstance(plan, WeeklyCandleRefreshPlan):
        raise TypeError("plan must be a WeeklyCandleRefreshPlan")
    outcomes = _validated_outcomes(checkpoint, plan)
    if len(outcomes) != len(plan.items):
        raise ValueError("Complete weekly checkpoint coverage is required")

    if history_start is not None:
        history_start = validate_aware_datetime(
            history_start, field_name="history_start"
        )
        if (
            history_start.utcoffset() != timedelta(0)
            or history_start.time() != datetime.min.time()
            or history_start >= plan.end
        ):
            raise ValueError("history_start must be UTC midnight before end")

    end_jd = connection.execute(
        "SELECT julianday(?)", (plan.end.isoformat(),)
    ).fetchone()[0]
    if end_jd is None:
        raise ValueError("Invalid end boundary")
    start_jd = None
    if history_start is not None:
        start_jd = connection.execute(
            "SELECT julianday(?)", (history_start.isoformat(),)
        ).fetchone()[0]
        if start_jd is None:
            raise ValueError("Invalid history_start boundary")
    bins = Counter()
    status_bins = Counter()
    failure_categories = Counter()
    row_total = 0
    recent_count = 0
    future_row_count = 0
    window_row_count = 0
    window_zero_count = 0
    start_proxy_count = 0
    end_proxy_count = 0
    both_proxy_count = 0
    series_gap_7_count = 0
    series_gap_30_count = 0
    gap_7_count = 0
    gap_30_count = 0
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

        if start_jd is not None:
            first_window_jd = None
            last_window_jd = None
            previous_jd = None
            series_gap_7 = False
            series_gap_30 = False
            for (day_jd,) in connection.execute(
                """SELECT julianday(timestamp) FROM candles
                   WHERE symbol = ? AND resolution = 'D'
                     AND julianday(timestamp) >= ? AND julianday(timestamp) < ?
                   ORDER BY julianday(timestamp)""",
                (symbol, start_jd, end_jd),
            ):
                window_row_count += 1
                if first_window_jd is None:
                    first_window_jd = day_jd
                if previous_jd is not None:
                    gap = day_jd - previous_jd
                    if gap > 7.000001:
                        gap_7_count += 1
                        series_gap_7 = True
                    if gap > 30.000001:
                        gap_30_count += 1
                        series_gap_30 = True
                last_window_jd = day_jd
                previous_jd = day_jd
            if first_window_jd is None:
                window_zero_count += 1
            else:
                at_start = first_window_jd - start_jd <= 7
                at_end = end_jd - last_window_jd <= 7
                start_proxy_count += at_start
                end_proxy_count += at_end
                both_proxy_count += at_start and at_end
            series_gap_7_count += series_gap_7
            series_gap_30_count += series_gap_30

    selected = len(plan.items)
    report = {
        "schema_version": 2 if history_start is not None else 1,
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
    if history_start is not None:
        report["history_start"] = history_start.isoformat()
        report["coverage"].update({
            "history_window_row_count": window_row_count,
            "history_window_zero_count": window_zero_count,
            "first_candle_within_7_calendar_days_of_start_count": start_proxy_count,
            "last_candle_within_7_calendar_days_of_end_count": end_proxy_count,
            "both_endpoint_proxy_count": both_proxy_count,
            "series_with_gap_over_7_calendar_days_count": series_gap_7_count,
            "gap_over_7_calendar_days_count": gap_7_count,
            "series_with_gap_over_30_calendar_days_count": series_gap_30_count,
            "gap_over_30_calendar_days_count": gap_30_count,
        })
        report["limitations"].append(
            "calendar-day gaps include market closures and do not prove missing exchange sessions"
        )
        report["limitations"].append(
            "late listings and delistings can lack one or both window endpoints without a data defect"
        )
    return report
