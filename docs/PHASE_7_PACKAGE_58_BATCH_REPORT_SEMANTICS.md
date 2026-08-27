# Phase 7 Package 58 - Batch Report Semantics

## Classification

IMPLEMENTATION.

## Operational evidence

The first controlled ten-year batch completed `SUCCESS` for 10 of 10
instruments in 7.980179 seconds: 25,120 candles downloaded, 21,354 inserted,
3,766 duplicates, and no failures. Its exact resume repeat completed `SUCCESS`,
skipped all 10 items, and took 0.000085 seconds.

The repeat exposed a report ambiguity: transfer totals described cumulative
checkpoint outcomes rather than current execution work.

## Versioned correction

Report schema version 2 separates `coverage.current_run` from
`coverage.cumulative`. Exact resume now reports zero attempted/downloaded/
inserted/duplicate current-run work while retaining cumulative batch evidence.
Checkpoint schema version 1, request correlation, persistence, resume, and
failure-isolation behavior are unchanged.

## Next step

Run one exact resume with schema-version-2 reporting. After verification,
select the automatic maintained-universe acquisition boundary.
