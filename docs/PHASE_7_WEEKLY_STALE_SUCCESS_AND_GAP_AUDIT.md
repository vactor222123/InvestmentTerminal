# Phase 7 — successful-but-stale and long-gap cohort audit

Classification: `AUDIT`. Fresh clean `develop` baseline:
`25c6a31cdd7b9e4a164c35632b1a63d8f0cb32bf`.

The user-returned redacted `WEEKLY_STORED_COHORTS` report has SHA-256
`51e855a6d61158e5f338e6494ca31f2ab59c11b44c566588a02e8dcd00307577`
and status `COMPLETE`. Its manifest/selection checksums and the half-open
`[2016-09-23T00:00:00Z, 2026-09-23T00:00:00Z)` window match the prior
stored-span report. The user separately reported `SQLite integrity: ok`.
No private manifest, checkpoint, database, symbol identity, or price was
inspected in this audit.

## Reconciled evidence

- First in-window observation: 4,457 within seven days of the start, 17
  after seven through 30 days, 220 after 30 through 365 days, and 7,198
  after 365 days; zero selected series have no in-window rows. These are
  stored-history offsets, not listing or ETF-inception dates.
- Endpoint combinations: 4,410 both, 47 start-only, 7,237 end-only, and
  198 neither. The 7,435 missing-start and 245 missing-end totals reconcile.
- Maximum consecutive-candle gap: 11,856 at most seven days, 12 over seven
  through 30 days, and 24 over 30 days. Thus 36 series have a gap over seven
  days. These are calendar intervals, not verified missing exchange sessions.
- All 214 weekly `FAILED` outcomes lack the end proxy: 42 `NO_PRICE_DATA`,
  140 `RESPONSE_NUMERIC`, and 32 `STORED_CANDLE_DRIFT`. The remaining 31
  missing-end series have weekly `SUCCESS`. All 36 long-gap series also have
  weekly `SUCCESS`. The report does not show whether those 31 and 36 overlap.

## Code boundary and interpretation

`WeeklyCandleRefreshService._refresh_one` obtains the latest stored candle,
requests a window beginning seven days earlier, rejects identity/window and
stored OHLCV drift, then saves the response. It returns `SUCCESS` whenever
the validated provider candle list is nonempty, even if every returned candle
already exists and the latest stored candle remains older than the seven-day
end proxy. The private checkpoint records downloaded, inserted, duplicate,
omitted-trailing, and stored counts, but no post-refresh freshness result.
Therefore `SUCCESS` means a valid nonempty transfer, not fresh endpoint
coverage or interior continuity. Changing that status now would alter the
existing private checkpoint contract without causal evidence.

The 36 long gaps could reflect market closures, halts, delisting/relisting,
provider history, or omitted data; the aggregate report cannot determine
which. Even an interval over 30 calendar days is a diagnostic priority, not
proof of missing exchange sessions. Neither these gaps nor the 31 stale
successes authorize automatic backfill, stored-candle overwrite, or a
scheduler-readiness claim.

## Smallest next boundary

Implement a separate, read-only, manifest/checkpoint-bound aggregate
diagnostic over **only** the union of weekly `SUCCESS` series lacking the
end proxy and weekly `SUCCESS` series with an interior gap over seven days.
Its union is at most 67 series; the overlap must be measured, not assumed.
Report privacy-safe staleness and largest-gap duration bins, their
intersection, and aggregate checkpoint downloaded/inserted/duplicate/
omitted-trailing counts for the selected cohorts. Preserve private identities
and exact per-series timestamps; emit only one versioned redacted report.
Reuse the existing read-only SQLite snapshot and validation rules, and add
focused, failure-path, and exact-binding tests. This is a diagnostic, not a
retry or new Yahoo request. Review the private result before selecting any
provider revalidation, calendar evidence, or weekly acceptance-policy change.
