# Phase 7 Package 63 - Resumable Universe Eligibility Scan

## Classification

IMPLEMENTATION.

## Result

The new `universe_eligibility_scan` operation validates the private Package 61
universe, binds its canonical checksum to one explicit 90-calendar-day window,
and processes a deterministic slice of at most 100 pending members. It reuses
the existing Yahoo candle client and does not accept a manual symbol list.

Every terminal member outcome is written to the private schema-version-1
checkpoint atomically before processing continues. Exact resume bypasses
`SUCCESS`, `EMPTY`, `FAILED`, and `PROJECTION_FAILED` outcomes. Provider and
payload failures remain isolated and contain only normalized exception types.

Successful private outcomes preserve source/Yahoo identity, observed bounds,
daily-candle and positive-volume-day counts, and median daily traded value
(`close * volume`). The schema-version-1 report exposes only current/cumulative
counts, checksums, request bounds, normalized failure categories, and progress
status `IN_PROGRESS | COMPLETE | FAILED`.

## Failure and privacy boundary

- a changed universe, window, schema, or corrupted outcome fails closed;
- every provider outcome is checkpointed independently;
- a report-write failure remains visible after the completed checkpoint write;
- the report contains no symbols, names, prices, paths, provider bodies, or
  exception messages;
- no SQLite candle persistence, ranking, selection, or ten-year batch exists in
  this package.

## Next step

Run one controlled private slice with `--max-items 100` and return only the
redacted report. Keep the Package 61 universe, eligibility checkpoint, yfinance
cache, and all member-level evidence private. Continue identical slices until
complete-universe coverage is measured; do not generate a ten-year batch.
