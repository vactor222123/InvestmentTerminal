# Phase 7 — weekly cohort result and indicator boundary audit

Classification: `AUDIT`. A fresh, clean GitHub `develop` clone matched the
caller baseline `2e9419617cf83fd9c58b5b73e0c7a3e5fcc486de`. The returned
redacted schema-1 `WEEKLY_STORED_COHORTS` report has SHA-256
`1f9cf22bcd152dee0c6bcc0d4a558fe1a2d71560596e9ba56bf104e6aeeef937`.
It is `COMPLETE` for all 11,892 selected series, with manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and selection checksum
`75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`,
over `[2016-09-29T00:00:00Z, 2026-09-29T00:00:00Z)`. The user separately
reported `SQLite integrity: ok`. No private manifest, checkpoint, database,
instrument identity, or price was inspected or changed in this package.

## Reconciled measurement

- First observed candle: 4,461 within seven days of the start, 17 after
  seven through 30 days, 225 after 30 through 365 days, and 7,189 after
  365 days; zero have no in-window rows. First observation is not listing or
  fund-inception evidence. In particular, the 7,189 must not be called
  missing history or automatically backfilled.
- Endpoint proxies: 4,449 both, 12 start-only, 7,338 end-only, and 93
  neither. Thus 7,431 lack the start proxy and 105 lack the end proxy.
- Largest consecutive-candle gap: 11,851 at most seven calendar days, 16
  over seven through 30 days, and 25 over 30 days. The 41 flagged series
  are not proven to be missing exchange sessions.
- Weekly outcomes reconcile: 11,805 `SUCCESS`, 45 `NO_PRICE_DATA`, one
  `RESPONSE_NUMERIC`, and 41 `STORED_CANDLE_DRIFT`. Within `SUCCESS`, 7,356
  lack the start proxy, 28 lack the end proxy, and 33 have a gap over seven
  days. These groups may overlap; the report does not establish their union.
  The prior coverage report counted 10,239 series with at least 200 stored
  rows, but does not intersect that count with recency and gaps.

## Code boundary

`weekly_stored_cohorts` and `weekly_stored_coverage` already validate the
complete manifest-bound checkpoint and scan SQLite read-only. Their reports
intentionally expose aggregate observation/proxy evidence, not per-series
analysis results. `weekly_stale_gap_diagnostic` can measure the overlap of
successful-but-stale and long-gap cohorts; repeating it for this end date
would not establish SMA availability or make the database usable for broad
downstream analysis. The older diagnostic already demonstrated that a weekly
`SUCCESS` is a valid nonempty transfer, not a freshness guarantee.

`TechnicalAnalysisService.analyze` calculates SMA50 and SMA200 from stored
candles for one symbol and labels `sufficient_for_long_term` when SMA200 is
non-null. Its `completeness_percent` is based on a 200-row count, not ten-year
coverage, exchange sessions, or freshness. No existing mass, versioned
per-series indicator projection was found in the inspected market-data and
technical-analysis paths. Do not infer that all 10,239 row-count-qualified
series have current, gap-free, or adjusted-price-valid indicators.

## Next bounded implementation

Implement a separate, deterministic **private latest-indicator projection**
for the selected daily series at an explicit exclusive UTC end. Reuse the
existing candle/indicator logic where its contracts fit; compute at most
objective values (at minimum latest close timestamp, SMA50, SMA200, sample
counts, currency, and explicit unavailable reasons), without trend verdicts,
trade recommendations, or automatic repair. Bind output to the manifest,
selection, end, and source checkpoint; persist private per-series results
atomically or transactionally, and emit a separate redacted aggregate report.
Keep existing weekly checkpoint and coverage JSON schemas unchanged. Focused
tests must cover 49/50 and 199/200 boundaries, stale observations, malformed
stored values, incomplete/mismatched checkpoint, write failure/rollback, and
redaction. Audit the exact persistence owner and adjusted-price semantics
before choosing the output table/file contract. Only after this projection
is measured should a weekly quality gate or unattended schedule be selected.

No Yahoo request, candle retry, stored-candle overwrite, new calendar claim,
or scheduler activation is authorized by this audit.
