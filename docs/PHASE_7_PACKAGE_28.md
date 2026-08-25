# Phase 7 Package 28 - Durable Transaction Import CLI/Report Audit

Package type: `AUDIT`.

Source baseline: `develop @ 2c8b5bfeb528dc7e8a902008d184382779de20b1`.

## Decision

The atomic repository boundary from Package 27 is sufficient for one bounded
durable import command. The smallest implementation is a transaction-specific
CLI and immutable schema-version-1 redacted result contract. No repository,
SQLite schema, valuation, workflow, or operational-baseline redesign is needed.

## Verified composition seams

The command can compose the existing `PortfolioTransactionCsvParser`,
`PortfolioTransactionSQLiteStore`, `SQLitePortfolioTransactionRepository`, and
`TransactionImportService`. It must require explicit `--input`, `--database`,
`--ledger-id`, `--portfolio-name`, `--base-currency`, `--imported-at`, and
`--output` values. Parsing must occur before database initialization so invalid
CSV does not create a database. Store metadata validation remains authoritative
for an existing database and must fail visibly on mismatch.

The existing operational baseline already inspects the transaction database
read-only and exposes schema version, total count, and earliest/latest occurrence
without payloads. Adding an import-report input or changing baseline schema 1
would duplicate evidence and is not justified.

## Required redacted report

The import report should distinguish `SUCCESS`, `EMPTY`, and `FAILED`, preserve
explicit run/import timestamps and duration, and expose only aggregate
`submitted`, `imported`, `duplicate`, and post-run stored counts plus
earliest/latest occurrence coverage. It must not serialize or print source or
database paths, filenames, transaction/source identities, instruments, ledger
or portfolio names, currencies, quantities, prices, cash amounts, references,
or raw rows. The existing `TransactionImportResult.to_dict()` is therefore an
internal result and must never be written or printed by the operational CLI.

Failure details require a privacy-safe normalization boundary. An executable
audit of the current qualification command confirmed that a missing input puts
the complete private path into `failure.reason`, despite the intended redacted
contract. Package 29 must add focused regression coverage and ensure neither the
new import report nor its console output leaks caller paths or private values.

## Cross-resource failure ownership

SQLite commit and JSON report replacement cannot be one atomic transaction.
If import commits and the later report write fails, the command must not claim
that SQLite rolled back. It must surface a distinct visible post-commit report
failure. Recovery is deterministic: repair the output destination and run the
same CSV again; immutable identities make the repeat all duplicates and create
a durable reconciled report without changing stored rows.

Before SQLite mutation, parser, metadata, and report-destination validation
failures must remain ordinary `FAILED` outcomes written atomically where
possible. A persistence exception during `add_batch` must roll back the whole
batch, write a redacted `FAILED` report, and exit non-zero. Tests must cover all
three stages separately so committed success is never represented as rollback.

## Smallest implementation package

Phase 7 Package 29 should add the versioned report model/service and one CLI,
plus focused tests for success, empty input, mixed duplicates, exact repeat,
metadata mismatch, later SQLite failure/rollback, parse-before-initialize,
privacy-safe failures, atomic report writing, and post-commit report-write
failure/reconciliation. It must not run the private import, generate valuations,
execute the review workflow, invoke AI, or authorize trading.

Only after Package 29 and its full suite are green may the user receive one
bounded PowerShell import block with explicit `SEND` report paths and `DO NOT
SEND` CSV/database paths.

## Verification

```text
focused transaction/baseline/privacy/atomic-write/architecture: 90 passed
full: 2,757 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
