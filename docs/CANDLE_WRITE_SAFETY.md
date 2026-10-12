# Candle write safety — audit A01/A04/A05

Classification: IMPLEMENTATION. Fresh clean `develop` baseline:
`52a9430e6d35e7b350d72d6969337dbf4b9bd987`.

## Bounded result

This package fixes three related unsafe write paths identified by the 2026-10-12
audit. No private runtime file was inspected or changed; no provider was called.
Existing JSON schemas and the SQLite schema are unchanged. No data migration,
repair of historical rows, split adjustment or automatic collection is performed.

## Repository contract

`CandleRepository.save` and nonempty `save_many` own one explicit
`BEGIN IMMEDIATE` transaction on the normal Database connection. They reject an
already active transaction without committing or rolling back caller-owned work.
Empty batches remain a zero-write no-op. Inputs are validated before starting writes.

The existing normalized `(symbol, resolution, timestamp)` key is unchanged.
Only an equal persisted OHLCV/currency payload is an idempotent duplicate.
`save` returns its original ID; `save_many` returns only newly inserted rows.
Different payloads raise `CandleConflictError`, a `sqlite3.IntegrityError` subtype,
with no identities or values in its message. No row is replaced or corrected.
Conflicts inside a batch are also detected. All new batch rows roll back on a
conflict, insertion error, or failed commit; a later save cannot commit the prefix.
Other integrity errors are no longer swallowed as duplicate-key success.

All three current save_many consumers were inspected: historical import,
projected historical import and weekly refresh. None requires a caller-owned
transaction. Import conflicts now propagate rather than becoming duplicate counts;
weekly persistence failures retain their existing stop-before-checkpoint behavior.
Previously hidden provider revisions can therefore become visible failures.
Do not bypass them or retry mass ingestion blindly.

## Weekly output contract

The direct `weekly_candle_refresh` CLI checks path safety before database/provider
work and again before checkpoint/report writers. Invalid paths return exit 1,
a fixed ASCII stderr message and NO report, even with `--json`.
The failure-report path cannot override this gate.

Guards cover resolved path equality, existing hardlink aliases, source-checkpoint
and cache directories, output symlinks/directories, and SQLite sidecar paths.
Each invocation requires a fresh report path; an existing report is preserved.
Resume still uses the same weekly checkpoint and end, with a NEW report filename.
The profile-based `weekly_run` already follows that convention. Safe unrelated
preflight failures still produce the existing redacted FAILED JSON contract.
Report write failures return exit 1 without exposing raw exception text.

These are safety checks for the existing single-operator workflow, not an
interprocess locking or hostile filesystem TOCTOU guarantee. A14 concurrency and
stale-lock recovery remain separate work. A report failure after a successful
database commit does not undo the database; preserve outputs and inspect the
checkpoint before resuming, as before.

## Evidence

- 51 new regression cases, covering each payload field through both save APIs,
  same-batch conflicts, rollback after insertion and deferred-constraint commit
  failures, caller transaction ownership, SQLite lock failure, and both import
  services. Output tests cover collisions, aliases, existing evidence, repeated
  validation and failed writers. Existing repeat-refresh test now uses a fresh
  report while retaining its no-extra-provider-call assertion.
- Focused: 118 passed in 5.24 s, including architecture/dependency guards.
- Full: 3764 passed, 4 skipped in 44.25 s; one existing Starlette warning.
- `git diff --check`: clean.
- No live SQLite integrity claim is made by this package.

The audit's `docs/audits/reproduce_20261012.py` remains historical characterization
for its specified old baseline. It is not a current acceptance suite and should
now fail on the repaired behavior; the regression tests above define correctness.

## Remaining scope and next step

A02 UTC canonicalization and A03 minor units remain open; current timestamp and
currency normalization are deliberately unchanged here. A07 source price basis,
backups, lifecycle composition and identity/split-aware valuation remain open.
After applying this package, return the applied SHA. Next audit the bounded
UTC/unit contract and migration implications before implementing it; do not read
or rewrite existing private rows automatically. No operational collection is needed
to validate this safety package.
