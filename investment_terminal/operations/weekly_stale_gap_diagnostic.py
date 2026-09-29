"""Read-only aggregate diagnostic for successful stale and long-gap series."""

from collections import Counter, defaultdict

from investment_terminal.operations.weekly_stored_coverage import (
    measure_weekly_stored_coverage,
)


_STALENESS_BINS = (
    "OVER_7_TO_14_DAYS", "OVER_14_TO_30_DAYS", "OVER_30_TO_90_DAYS",
    "OVER_90_DAYS", "NO_WINDOW_ROWS",
)
_GAP_BINS = ("OVER_7_TO_30_DAYS", "OVER_30_TO_90_DAYS", "OVER_90_DAYS")
_GROUPS = ("STALE_ONLY", "GAP_ONLY", "BOTH")
_COUNTER_FIELDS = (
    ("downloaded_total", "downloaded"),
    ("inserted_total", "inserted"),
    ("duplicate_total", "duplicates"),
    ("omitted_trailing_total", "omitted_trailing_count"),
)


def measure_weekly_stale_gap_diagnostic(
    plan, checkpoint, connection, *, history_start,
):
    """Measure only SUCCESS cohort intersections; never expose identities."""
    if history_start is None:
        raise ValueError("Explicit history_start is required")
    staleness_bins = Counter()
    gap_bins = Counter()
    groups = defaultdict(Counter)

    def observe(first, last, largest_gap, outcome, start, end):
        if outcome["status"] != "SUCCESS":
            return
        stale = last is None or end - last > 7
        long_gap = largest_gap > 7.000001
        if not stale and not long_gap:
            return
        if stale:
            if last is None:
                staleness_bin = "NO_WINDOW_ROWS"
            elif end - last <= 14:
                staleness_bin = "OVER_7_TO_14_DAYS"
            elif end - last <= 30:
                staleness_bin = "OVER_14_TO_30_DAYS"
            elif end - last <= 90:
                staleness_bin = "OVER_30_TO_90_DAYS"
            else:
                staleness_bin = "OVER_90_DAYS"
            staleness_bins[staleness_bin] += 1
        if long_gap:
            if largest_gap <= 30.000001:
                gap_bin = "OVER_7_TO_30_DAYS"
            elif largest_gap <= 90.000001:
                gap_bin = "OVER_30_TO_90_DAYS"
            else:
                gap_bin = "OVER_90_DAYS"
            gap_bins[gap_bin] += 1
        group = "BOTH" if stale and long_gap else (
            "STALE_ONLY" if stale else "GAP_ONLY"
        )
        groups[group]["series_count"] += 1
        for report_field, checkpoint_field in _COUNTER_FIELDS:
            groups[group][report_field] += outcome[checkpoint_field]

    base = measure_weekly_stored_coverage(
        plan, checkpoint, connection, history_start=history_start,
        _cohort_observer=observe,
    )
    stale_count = sum(staleness_bins.values())
    gap_count = sum(gap_bins.values())
    intersection = groups["BOTH"]["series_count"]
    union = sum(groups[group]["series_count"] for group in _GROUPS)
    if stale_count + gap_count - intersection != union:
        raise ValueError("Diagnostic cohort counts do not reconcile")
    return {
        "schema_version": 1,
        "operation_identity": "WEEKLY_STALE_GAP_DIAGNOSTIC",
        "status": "COMPLETE",
        "manifest_checksum": base["manifest_checksum"],
        "selection_checksum": base["selection_checksum"],
        "history_start": base["history_start"],
        "end": base["end"],
        "selected_series_count": base["coverage"]["selected_series_count"],
        "stale_success_count": stale_count,
        "long_gap_success_count": gap_count,
        "intersection_count": intersection,
        "union_count": union,
        "staleness_bins": [
            {"bucket": key, "count": staleness_bins[key]}
            for key in _STALENESS_BINS
        ],
        "largest_gap_bins": [
            {"bucket": key, "count": gap_bins[key]} for key in _GAP_BINS
        ],
        "disjoint_groups": [
            {"group": key, "series_count": groups[key]["series_count"], **{
                report_field: groups[key][report_field]
                for report_field, _ in _COUNTER_FIELDS
            }}
            for key in _GROUPS
        ],
        "failure": None,
        "limitations": [
            "SUCCESS means a nonempty valid response, not a fresh candle",
            "calendar-day gaps do not prove missing exchange sessions",
            "report excludes identities, prices, currencies, paths, and exact per-series dates",
        ],
    }
