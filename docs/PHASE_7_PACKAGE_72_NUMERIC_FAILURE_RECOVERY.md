# Phase 7 Package 72 - Numeric-Failure Recovery

## Classification

IMPLEMENTATION.

## Result

Eligibility checkpoint and redacted report schema version 4 implement the
bounded recovery selected by Package 71. Loading schema version 3 atomically
migrates only terminal `RESPONSE_NUMERIC` outcomes below four attempts to
`RETRY_PENDING` before any provider request. Identity, attempt count, measured
time, null metrics, and failure category are retained; every other outcome is
preserved unchanged.

A numeric retry that passes the production candle contract becomes terminal
`SUCCESS` or `EMPTY` evidence at attempt four. A repeated numeric defect becomes
`FINAL_FAILED` at attempt four. Other retryable and terminal categories retain
their three-attempt limit. Malformed schema-version-4 attempt/category
combinations fail closed, retry-first ordering and the 100-item bound remain in
force, and exact resume bypasses terminal outcomes.

The historical single-series diagnostic remains read-only compatible with
schema version 3 and cannot migrate its input. The implementation package does
not query Yahoo, mutate runtime evidence, run slice 002, rank instruments, or
start ten-year ingestion.

## Verification

- focused operation, CLI, diagnostic, and architecture checks: 43 passed;
- complete suite: 2,884 passed, four skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next step

Apply the package to the operator checkout. Run exactly one schema-4
revalidation item against the existing private universe/checkpoint and return
only its redacted report. Review that result before draining further numeric
outcomes or starting slice 002.
