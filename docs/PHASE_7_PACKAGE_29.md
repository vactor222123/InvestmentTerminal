# Phase 7 Package 29 - Bounded Durable Transaction Import

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ 8ec2f2f8c203c68b6f7dee6cb1a146f2bb1e3b73`.

## Result

The new `investment_terminal.cli.transaction_csv_import` command composes the
canonical CSV parser, schema-version-1 SQLite store, atomic repository batch
append, and import service for one explicit file. It requires caller-owned
ledger ID, portfolio name, base currency, import time, database, and report
destination. Parsing completes before database initialization; empty or invalid
input does not create a transaction database.

`TransactionCsvImportResult` is an immutable schema-version-1 operational
contract with `SUCCESS`, `EMPTY`, and `FAILED` states. Its report contains only
run/import timing, submitted/imported/duplicate/stored counts, and stored
earliest/latest occurrence coverage. It excludes paths, filenames, transaction
and source identities, instruments, ledger/portfolio metadata, currencies,
quantities, prices, cash values, references, and raw rows. The internal
`TransactionImportResult.to_dict()` is never exported.

Expected immutable-identity conflicts remain row-aligned duplicates. Metadata
mismatch and persistence failures are visible and redacted. A simulated later
SQLite trigger failure rolls back the whole new batch. Exact repeat imports zero
rows, reports every submitted row as duplicate, and leaves stored coverage
unchanged.

The confirmed qualification-report path leak is also closed: missing-input and
validation failures now use stable privacy-safe reasons. Focused tests verify
that reports and console JSON do not expose caller paths or private values.

## Cross-resource recovery

SQLite commit and JSON report replacement cannot share one transaction. If the
import commits and report replacement then fails, the CLI raises
`TransactionImportReportAfterCommitError` and does not claim rollback. After
repairing the output destination, repeating the exact input creates a reconciled
all-duplicate report without changing the stored ledger.

## Scope boundary

This package does not read private runtime inputs, initialize the operational
database, generate valuations, execute a workflow, invoke AI, access a broker,
or authorize trading. The next step is one user-executed bounded private import;
only its redacted report may be returned for review.

## Verification

```text
focused transaction/baseline/privacy/atomic-write/architecture: 100 passed
full: 2,767 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
