# Phase 7 Package 27 - Atomic Repository Batch Append

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ e84b0c91ca4d752db1ced22e8ab8539181d3fa1f`.

## Scope

This package adds one persistence-agnostic `add_batch` contract to
`PortfolioTransactionRepository`, implements it in both adapters, and routes
`TransactionImportService` through the new boundary. It does not add a CLI or
report, read private runtime inputs, initialize the operational database,
generate valuations, execute a workflow, or authorize trading.

## Implemented behavior

- outcomes align one-for-one with submitted rows;
- existing identities and later repeats inside the batch report `False`;
- the first new occurrence reports `True`;
- in-memory state is validated and staged before one final publication;
- SQLite serializes inputs first and performs all inserts in one transaction;
- primary-key duplicates use `INSERT OR IGNORE` without replacing originals;
- unexpected SQLite errors remain visible and roll back every new batch row;
- single-row `add` retains its existing return and duplicate exception;
- `TransactionImportResult.to_dict()` remains unchanged;
- SQLite schema version 1 requires no migration.

## Failure-path evidence

A SQLite trigger aborting a later row proves durable all-or-nothing behavior.
After reopening the database, the earlier candidate is absent, the failing row
is absent, and a row committed before the batch is unchanged. Separate tests
cover mixed new/existing rows, repeated identities, complete-input validation,
and exact-repeat idempotency.

## Next boundary

Audit the smallest bounded durable import CLI/report and user-executed private
runtime handoff. That audit must define atomic failure reporting, redaction,
exact-repeat evidence, and baseline projection before implementation or any
operational database mutation.

## Verification

```text
focused transaction/import/qualification/architecture: 57 passed
full: 2,757 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
