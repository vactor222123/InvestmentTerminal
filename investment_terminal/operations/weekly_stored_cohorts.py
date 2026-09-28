"""Redacted observed-history cohorts from the existing stored-coverage scan."""

from collections import Counter, defaultdict

from investment_terminal.operations.weekly_stored_coverage import (
    measure_weekly_stored_coverage,
)


_AGE_BINS = (
    "WITHIN_7_DAYS", "OVER_7_TO_30_DAYS", "OVER_30_TO_365_DAYS",
    "AFTER_365_DAYS", "NO_ROWS",
)
_ENDPOINT_BINS = ("BOTH", "START_ONLY", "END_ONLY", "NEITHER")
_GAP_BINS = ("NO_GAP_OVER_7_DAYS", "GAP_OVER_7_TO_30_DAYS", "GAP_OVER_30_DAYS")


def measure_weekly_stored_cohorts(plan, checkpoint, connection, *, history_start):
    """Classify observations, never infer listing age or missing sessions."""
    ages = Counter()
    endpoints = Counter()
    gaps = Counter()
    by_outcome = defaultdict(Counter)

    def observe(first, last, largest_gap, outcome, start, end):
        if first is None:
            age = "NO_ROWS"
        elif first - start <= 7:
            age = "WITHIN_7_DAYS"
        elif first - start <= 30:
            age = "OVER_7_TO_30_DAYS"
        elif first - start <= 365:
            age = "OVER_30_TO_365_DAYS"
        else:
            age = "AFTER_365_DAYS"
        at_start = first is not None and first - start <= 7
        at_end = last is not None and end - last <= 7
        if at_start and at_end:
            endpoint = "BOTH"
        elif at_start:
            endpoint = "START_ONLY"
        elif at_end:
            endpoint = "END_ONLY"
        else:
            endpoint = "NEITHER"
        if largest_gap > 30.000001:
            gap_bin = "GAP_OVER_30_DAYS"
        elif largest_gap > 7.000001:
            gap_bin = "GAP_OVER_7_TO_30_DAYS"
        else:
            gap_bin = "NO_GAP_OVER_7_DAYS"
        category = (
            outcome["category"] if outcome["status"] == "FAILED"
            else outcome["status"]
        )
        ages[age] += 1
        endpoints[endpoint] += 1
        gaps[gap_bin] += 1
        by_outcome[category]["count"] += 1
        by_outcome[category]["missing_start_proxy_count"] += not at_start
        by_outcome[category]["missing_end_proxy_count"] += not at_end
        by_outcome[category]["gap_over_7_days_count"] += largest_gap > 7.000001

    if history_start is None:
        raise ValueError("Explicit history_start is required")
    base = measure_weekly_stored_coverage(
        plan, checkpoint, connection, history_start=history_start,
        _cohort_observer=observe,
    )
    selected = base["coverage"]["selected_series_count"]
    if not all(sum(group.values()) == selected for group in (ages, endpoints, gaps)):
        raise ValueError("Cohort coverage is incomplete")
    return {
        "schema_version": 1,
        "operation_identity": "WEEKLY_STORED_COHORTS",
        "status": "COMPLETE",
        "manifest_checksum": base["manifest_checksum"],
        "selection_checksum": base["selection_checksum"],
        "history_start": base["history_start"],
        "end": base["end"],
        "selected_series_count": selected,
        "first_observation_age_bins": [
            {"bucket": key, "count": ages[key]} for key in _AGE_BINS
        ],
        "endpoint_proxy_bins": [
            {"bucket": key, "count": endpoints[key]} for key in _ENDPOINT_BINS
        ],
        "largest_observed_gap_bins": [
            {"bucket": key, "count": gaps[key]} for key in _GAP_BINS
        ],
        "weekly_outcome_intersections": [
            {"category": key, **dict(sorted(counts.items()))}
            for key, counts in sorted(by_outcome.items())
        ],
        "failure": None,
        "limitations": [
            "observation age is not listing or fund-inception age",
            "calendar-day gaps do not prove missing exchange sessions",
            "endpoint proxies do not prove continuous or analysis-ready history",
            "report excludes identities, prices, currencies, paths, and exact per-series dates",
        ],
    }
