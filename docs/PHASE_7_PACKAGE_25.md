# Phase 7 Package 25 — Bounded Transaction CSV Qualification

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ 8c718ca22495dc34ee70e3dd58038884a6ce8378`.

## Result

The new `investment_terminal.cli.transaction_csv_qualification` command parses
one private canonical CSV without initializing or modifying SQLite. Its atomic
schema-version-1 report distinguishes `SUCCESS`, `EMPTY`, and `FAILED` and
preserves only qualification/run times, aggregate count, ordered type counts,
and earliest/latest occurrence time.

The report excludes source path/name, transaction IDs, instruments, quantities,
prices, cash amounts, references, and raw rows. Failure is written before a
non-zero exit. A synthetic example is tracked; the canonical private working
filename is Git-ignored and protected by tests.

Qualification does not persist transactions, prove atomic batch-import
readiness, generate valuations, execute a workflow, invoke AI, or authorize
trading.

## Selected Next Step

Run one user-owned CSV through the command and return only the redacted report.
Do not return the private CSV. Database ingestion remains prohibited until the
result is reviewed and a later package establishes atomic durable batch import.

## Verification

```text
focused qualification/parser/import/models/privacy/architecture: 49 passed
full: 2,752 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
