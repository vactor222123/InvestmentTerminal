# Phase 7 Package 33 - Bounded Transaction-Derived Valuation

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ 0169bdf0c49a7f58c607a5eeed6b299144f1965a`.

## Result

`TransactionDerivedValuationService` now composes the established transaction
ledger, position reconstruction, realised/unrealised calculations, explicit
offline quotes, immutable valuation snapshot, and append-only SQLite repository.
It fails closed on transactions after `valued_at`, quote identity/currency/time
defects, calculation errors, ownership mismatches, and duplicate snapshots.

The CLI requires explicit private input/database paths and writes an atomic
schema-version-1 redacted report. The report exposes timing and only transaction,
open-position, quote, currency, and stored-snapshot counts. It excludes paths,
identities, instruments, quantities, prices, and monetary results. A committed
snapshot followed by report-write failure raises a distinct recovery error.

Live quotes, FX conversion, inferred freshness, cash valuation, workflow
execution, analysis, and trading remain out of scope.

## Verification

```text
initial focused: 57 passed, 2 failed (synthetic canonical-key fixture defect)
focused rerun: 59 passed
full: 2,775 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```

## Next step

Audit and qualify one private offline quote JSON against the reconstructed open
position requirements without creating a valuation snapshot. Do not execute the
private valuation until quote coverage, identity, currency, and time evidence
has been reviewed through a redacted report.
