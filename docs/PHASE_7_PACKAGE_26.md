# Phase 7 Package 26 - Atomic Transaction Batch Import Audit

Package type: `AUDIT`.

Source baseline: `develop @ 5cba060e45fa39c8889b8bcedc2683d091dd3c96`.

## Operational checkpoint

The controlled private canonical CSV qualification completed successfully before
this package. Its redacted evidence reports 62 events: 29 `BUY`, 2 `SELL`, and
31 `FEE`, spanning `2026-05-05T16:38:00Z` through
`2026-08-21T16:28:00Z`. The private CSV and source documents remain outside
Git and the package ZIP. No transaction database has been initialized or
modified.

## Verified existing behavior

`TransactionImportService.import_batch` processes input rows sequentially. For
each row it calls `repository.get`, then `repository.add`; an existing identity
or an intercepted `ValueError` is counted as a duplicate. Imported and duplicate
identities preserve input order, repeated identities within one batch remain
visible, and an exact repeat is idempotent.

`SQLitePortfolioTransactionRepository.add` serializes and commits one row inside
one `PortfolioTransactionSQLiteStore.transaction`. The store correctly rolls
back a failure inside that single transaction. Schema version 1 already has the
required immutable primary key and indexes.

## Blocking gap

There is no repository-level batch append operation. Each successful `add`
commits before the next input is attempted, so a later unexpected exception
cannot roll back earlier rows from the same import batch. An executable audit
with a simulated failure on the second add preserved the first identity:

```text
ERROR=simulated persistence failure
PERSISTED_AFTER_FAILURE=('a',)
```

Existing rollback coverage proves only one manually owned store transaction;
it does not exercise `TransactionImportService` against a durable multi-row
failure. Catching every repository `ValueError` as a duplicate also makes the
service, rather than the persistence boundary, responsible for interpreting
identity conflicts.

## Smallest safe implementation package

Phase 7 Package 27 should add one persistence-agnostic atomic batch append
contract to `PortfolioTransactionRepository` and implement it in both reference
repositories. The result must remain aligned with every submitted row so the
existing import result can preserve imported and duplicate identities,
including repeated identities inside one batch.

The SQLite implementation must own one `store.transaction` for the complete
batch. Expected primary-key conflicts are duplicates; any other exception must
roll back every newly inserted row. The in-memory implementation must stage and
publish state only after complete success. Existing single-add behavior and
public `TransactionImportResult` JSON must remain compatible.

Focused tests must cover mixed new/existing identities, repeated identities,
exact-repeat idempotency, an unexpected failure after an earlier candidate row,
durable rollback/reopen verification, and preservation of the original row on
identity conflict.

Package 27 must not add a CLI or redacted import report, read private runtime
inputs, initialize the operational database, generate valuations, or execute a
workflow. Those actions remain blocked until atomic batch behavior is proven.

## Verification

```text
focused transaction import/repository/SQLite/parser/qualification/architecture:
52 passed
executable failure audit: partial persistence reproduced
full: 2,752 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
