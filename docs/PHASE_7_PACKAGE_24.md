# Phase 7 Package 24 — Portfolio-Transaction Operational Input Audit

Package type: `AUDIT`.

Source baseline: `develop @ 544ee79f5c231199339c780ee84481aea38c531b`.

## Decision

The repository has complete provider-neutral transaction domain and persistence
building blocks, but no safe user-facing operational qualification or import
composition root. No private transaction input may be requested or imported
through ad hoc Python composition.

## Verified Existing Boundaries

`PortfolioTransactionCsvParser` parses the canonical 15-column UTF-8 CSV,
accepts `BUY`, `SELL`, `DIVIDEND`, and `FEE`, constructs typed instrument
identities, requires timezone-aware occurrence times, preserves input order and
duplicates, and reports invalid rows with their CSV line number.

`TransactionImportBatch` preserves an explicit timezone-aware import time.
`TransactionImportService` accounts for imported and duplicate transaction
identities and is idempotent for an exact repeat. The public result, however,
contains complete imported and duplicate transaction IDs and is therefore not a
redacted shareable artifact.

`PortfolioTransactionSQLiteStore` owns schema version `1`, immutable ledger
metadata, WAL configuration, and rollback for one repository operation.
`SQLitePortfolioTransactionRepository` stores strict deterministic JSON,
rejects identity replacement, supports ordered time/instrument queries, and
reconstructs the typed ledger after restart.

The operational baseline already accepts `--transaction-database` and projects
only schema, total count, and earliest/latest occurrence times. It opens the
configured database read-only and reports `READY`, `ABSENT`, or `ERROR` without
serializing transaction IDs, instruments, amounts, or payloads.

## Measured Gaps

- no transaction-specific CLI exists under `investment_terminal.cli`;
- no tracked canonical transaction example CSV exists;
- no versioned atomic transaction qualification/import report exists;
- repository privacy tests and `.gitignore` cover current portfolio working
  files but define no canonical repository-local transaction filename;
- the returned current operational baseline has
  `PORTFOLIO_TRANSACTIONS=ABSENT` because no transaction database was supplied;
- `TransactionImportService` appends one transaction at a time. Each append is
  atomic, but a later unexpected failure can leave earlier batch items
  committed. Therefore it does not provide an all-or-nothing durable batch
  import guarantee required for controlled private operational ingestion.

The absence of a CLI and durable report prevents a safe user-executed
qualification. The missing batch transaction boundary prevents moving directly
to persistence even after a CSV parses successfully.

## Selected Next Package

```text
Phase 7 Package 25 — Bounded Transaction CSV Qualification
```

Add one parse-only CLI over the existing parser plus a tracked synthetic example
CSV and an atomic schema-version-1 redacted report. The report should preserve
`SUCCESS`, `EMPTY`, and `FAILED`, requested qualification time, aggregate row
count, type counts, and earliest/latest occurrence times, while excluding the
source path/name, transaction IDs, instruments, quantities, prices, cash
amounts, source references, and raw rows. A failed report must be written before
non-zero exit.

Package 25 must not initialize or modify a transaction database. Atomic SQLite
batch import, import-report design, and exact-repeat persistence verification
remain a later separately audited remediation. Valuation generation, workflow
execution, another instrument, scheduling, mass refresh, AI, broker access, and
trading remain out of scope.

## Verification

```text
focused transaction/parser/persistence/baseline/privacy/architecture: 81 passed
full: 2,743 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
