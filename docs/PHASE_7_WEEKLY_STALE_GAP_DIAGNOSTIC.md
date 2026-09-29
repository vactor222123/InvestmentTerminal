# Phase 7 — bounded successful-stale and long-gap diagnostic

Classification: `IMPLEMENTATION`. Fresh clean `develop` baseline:
`36c39f1603f434d64772332f2c0221dc32728618`.

The returned redacted ten-year cohort report measured 31 weekly `SUCCESS`
series lacking the end proxy and 36 weekly `SUCCESS` series with an interior
gap over seven calendar days. Their overlap is unknown; current-data union
cannot exceed 67. The 214 weekly failures are a separate cohort and are not
selected here. `SUCCESS` means a valid nonempty response, not a fresh candle.

`python -m investment_terminal.cli.weekly_stale_gap_diagnostic` is a separate
read-only CLI. It reconstructs the exact manifest-bound source selection,
requires the complete matching weekly checkpoint and explicit UTC-midnight
history start, opens the existing SQLite database with `mode=ro` and
`query_only`, and holds one read transaction. It reuses the validated
stored-coverage scan and observes only aggregate facts for `SUCCESS` series
that are stale at the end, have a gap over seven calendar days, or both.
No Yahoo request, candle insertion, checkpoint update, or SQLite migration
occurs. Existing coverage/cohort report schemas and weekly status semantics
are unchanged.

The separate `WEEKLY_STALE_GAP_DIAGNOSTIC` schema-version-1 report binds
manifest/selection checksums and the half-open window. It reports stale and
long-gap counts, their intersection and union, staleness and largest-gap
duration bins, and three disjoint groups (`STALE_ONLY`, `GAP_ONLY`, `BOTH`).
Each group contains only series count and aggregate checkpoint downloaded,
inserted, duplicate, and omitted-trailing totals. Identities, currencies,
prices, exact per-series timestamps, paths, and provider text are excluded.
Invalid binding, incomplete checkpoint, invalid stored timestamp/currency,
invalid start, or SQLite failure produces a redacted `FAILED` report.

This report can distinguish, for example, a successful transfer with zero
new inserts from one with new rows, but cannot determine why a provider lacks
newer history or whether a calendar gap contains missing exchange sessions.
It does not license backfill, retry, overwrite, or unattended weekly updates.
Next: one exact-baseline user-executed private read-only qualification and
review of only the redacted report plus independent SQLite integrity.
