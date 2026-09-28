# Phase 7 — ten-year stored-span result audit

Classification: `AUDIT`. Fresh clean `develop` baseline:
`27b15d6f3ff828e5ffb1850614b92f68b7fdd707`.

The user-returned redacted `WEEKLY_STORED_COVERAGE` schema-2 report has
SHA-256 `3145b6dc6bf11d48a479054d54ca629335747a3fced6aba7fbd6d00e875366f4`
and status `COMPLETE`. It binds manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and selection checksum
`75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`
to the half-open window
`[2016-09-23T00:00:00Z, 2026-09-23T00:00:00Z)`. No private database,
manifest, checkpoint, or member identity was inspected. A separate SQLite
integrity result was not returned with this report, so this audit makes no
new integrity claim.

## Measured facts and reconciliation

- 11,892 selected series have 17,242,630 rows inside the window and zero
  window-empty series. The all-history count before the exclusive end is
  17,300,242; the difference is 57,612 earlier rows.
- The row-count bins reconcile: 0 + 326 + 1,345 + 10,221 = 11,892.
  Thus 11,566 have at least 50 stored rows and 10,221 have at least 200.
- 4,457 series have a first in-window candle within seven calendar days of
  the start; 11,647 have a last in-window candle within seven calendar days
  of the end; 4,410 satisfy both endpoint proxies. The derived disjoint
  groups are 47 start-only, 7,237 end-only, and 198 neither. Therefore
  7,435 lack the start proxy and 245 lack the end proxy.
- 36 series have at least one consecutive-candle interval over seven
  calendar days (95 such intervals). Of these, 24 series have an interval
  over 30 calendar days (24 such intervals).
- The weekly checkpoint outcomes reconcile: 11,678 `SUCCESS` and 214
  `FAILED`; the failures comprise 42 `NO_PRICE_DATA`, 140
  `RESPONSE_NUMERIC`, and 32 `STORED_CANDLE_DRIFT`.

## Interpretation boundary

Only about 37.1% (4,410/11,892) meet both *endpoint proxies*. This is not
the percentage of ten-year-complete or analysis-ready series. A late listing
or ETF launch can legitimately lack the start endpoint; the report contains
no listing/inception dates. Calendar-day gaps can include closures, halts,
or delistings and do not identify missing exchange sessions. Row counts do
not establish valid SMA-50/SMA-200 values, adjusted-price correctness, or
per-series continuity. The report does not reveal whether the 245 stale-end
series, 36 gap series, and 214 weekly failures overlap.

## Smallest next boundary

Select a separate, read-only, privacy-safe cohort measurement over the same
manifest/checkpoints and SQLite snapshot. It should report mutually exclusive
first-observation age bins, endpoint-proxy combinations, gap-duration bins,
and intersections with weekly outcome categories, without symbols, prices,
currencies, exact per-series dates, or paths. Keep the existing schema-1 and
schema-2 reports unchanged; any new report must have an explicit versioned
contract and focused/failure-path tests. This measurement can prioritize
targeted quality checks but still cannot prove listing dates or exchange-
session completeness. Do not initiate another mass Yahoo collection, infer
7,435 data defects, or enable unattended weekly refresh from this result.
