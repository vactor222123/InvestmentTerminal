# Phase 7 — observed-history cohort measurement

Classification: `IMPLEMENTATION`. Fresh clean `develop` baseline:
`9bc6644bda3a48ac655d67f55b0909f26144328c`.

The prior redacted ten-year span report measured 4,410 series with both
seven-calendar-day endpoint proxies, 7,435 without the start proxy, 245
without the end proxy, and 36 with an interior gap over seven calendar days.
It could not show how those cohorts overlap or distinguish late listings from
missing provider history. The user collected the candles over multiple days;
these observations refer to candle timestamps, not download times.

This package adds `python -m investment_terminal.cli.weekly_stored_cohorts`.
It reconstructs the same manifest-bound selection and requires the complete
weekly checkpoint and an explicit UTC-midnight start before the exclusive
end. It opens the existing SQLite database read-only under one transaction,
uses the existing validated stored-coverage scan, and publishes a separate
atomic redacted `WEEKLY_STORED_COHORTS` schema-version-1 report. Existing
`WEEKLY_STORED_COVERAGE` schema 1 and 2 remain unchanged. No Yahoo request,
checkpoint mutation, candle insertion, or schema migration is involved.

The cohort report has deterministic aggregate bins for first *observed*
in-window candle offset (within 7, over 7–30, over 30–365, after 365, or no
rows), the four start/end proxy combinations, and the largest observed
consecutive-candle gap (at most 7, over 7–30, or over 30 calendar days). For each
weekly outcome category it reports count, missing-start, missing-end, and
gap-over-seven intersections. Every bin family reconciles to the selected
series count. The report contains no symbols, currencies, prices, paths,
exact per-series dates, or exception text. Invalid binding, start, stored
timestamps/currency, or SQLite access fails into a redacted report.

The bins classify *stored observations*, not instrument listing or ETF
inception dates. Calendar intervals do not prove missing exchange sessions;
no adjustment quality, SMA result, or analysis-readiness claim follows from
them. This reusable read-only command can be run against later complete weekly
checkpoints, but it is not wired to an automatic scheduler yet. Next: prepare
one exact-baseline private operational handoff, then review its redacted
aggregate report and independent SQLite integrity before targeted remediation
or scheduling.
