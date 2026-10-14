# Candle UTC storage and legacy compatibility gate

Classification: IMPLEMENTATION. Fresh clean `develop` baseline:
`f473834faa609db55aedf534881989f13afa5a92`.
Implements the A02 repository/provider boundary selected by the compatibility
audit. No private runtime inspection, provider request, schema migration or
historical-row rewrite was performed. A03 source units remain open.

## Implemented contract

- New repository candle inputs and non-null query bounds must be timezone-aware
  and representable as UTC at microsecond precision. Convert the instant with
  `astimezone`, never attach a guessed timezone. Models are not mutated.
- Persist stdlib UTC `isoformat()` keys: `+00:00`, seconds when microseconds are
  zero, otherwise exactly six fractional digits. This retains existing canonical
  UTC bytes and IDs and preserves chronological TEXT order across second and
  fractional-second boundaries. Equivalent offset inputs use the same key.
- Exact payload replay remains a no-op; different payloads at an equivalent
  instant raise `CandleConflictError`. Every new row in a failed batch rolls back.
- Before save/save_many, stream stored timestamps for each affected normalized
  symbol/resolution once inside the owned `BEGIN IMMEDIATE` transaction, before
  the first insert. Every timestamp must parse and round-trip to the canonical
  form. Naive, offset, malformed, alternative UTC spelling, truncated precision
  or duplicate-instant aliases block with `CandleTimestampCompatibilityError`.
- `get`, `get_latest`, `get_earliest` and `get_range` use the same series gate
  and selection within one SQLite read snapshot. Caller-owned transactions are
  neither committed nor rolled back. An ID lookup does not certify a row while
  ignoring incompatible timestamps elsewhere in its series. A restricted range
  cannot hide an incompatible row outside its window.
- No validation cache survives an operation: later external commits and reopen
  are rechecked. Other series are not scanned or blocked. `count` remains a raw
  row count, not certification; delete semantics and empty-batch no-op are unchanged.

The timestamp check is O(stored rows in the affected series) per operation with
constant streaming memory, using the existing symbol/resolution index. It is NOT
performed per incoming candle. Weekly latest/range/write operations each check
their snapshot. There is intentionally no unversioned persistent certification
cache. Full-universe runtime overhead has not been measured; indexed lookup of
the selected row itself remains intact but is no longer the complete read cost.

## Provider and consumer behavior

Yahoo projection rejects naive, NaT, absent-offset, out-of-range and submicrosecond
source timestamps as existing `RESPONSE_TIMESTAMP`. Strict and trailing-omission
paths use the same helper; a timestamp defect cannot become an omitted numeric
row. Valid aware offsets still convert to UTC. No new failure category or JSON
schema is introduced. Request-window serialization/checksums are unchanged.

Both historical import services retain their existing conflict/error propagation.
Weekly refresh already rethrows sqlite errors before checkpoint publication;
the compatibility error subclasses `sqlite3.DatabaseError`. A bad stored series
therefore stops at repository read before provider access, not as a successful
empty response or a terminal provider failure. No automatic retry is added.

## Limits and recovery

This is a repository/API guard, not a database CHECK constraint or protection
against arbitrary SQL/triggers. Direct-SQL readers outside CandleRepository
retain their own validation contracts. It does not certify the entire existing
private corpus, price basis, units, session completeness or freshness.

On compatibility failure preserve the database and checkpoint. Do not delete
rows, blindly retry, or automatically rewrite `Z`/offset/naive values. A separate
authorized read-only inventory and backup-aware migration decision is required.
Even equal-payload duplicate instants are not merged by this package; unequal
payloads need explicit conflict resolution and naive values need source evidence.
Current UTC-conforming data needs no migration. Existing JSON, request hashes,
manifests, checkpoints, OHLCV and currency behavior are unchanged.

## Verification and next step

Six A02 audit probes are promoted to ordinary regression tests with unchanged
expectations. The two A03 expected failures remain explicitly open. New tests
cover legacy format/API combinations, no-write failures, conflicting duplicate
instants, canonical legacy byte/ID preservation, subsecond boundaries, DST-like
offsets, invalid precision/range, transaction ownership, per-series indexed scan
count, WAL concurrent mutation, reopen, both imports and weekly stop behavior.

After applying, return the applied SHA. Next implement A03 source-unit safety
upstream of uppercase conversion, accounting for previously successful currency
checkpoints. Do not start live collection or auto-migrate private history merely
because synthetic UTC tests pass.

Verification: final focused 253 passed, 2 xfailed (6.91 s), including architecture
and dependency guards; final full 3875 passed, 4 skipped, 2 xfailed (39.23 s),
one existing Starlette deprecation warning. `git diff --check` clean.
100 new cases plus six promoted A02 probes. The first full run was 3873 passed,
1 failed, 4 skipped, 2 xfailed: an older historical-evidence test tried to seed
a naive value through save, which now correctly rejects it. Its independent
consumer rejection remains tested through injection; an additional raw-SQL
legacy fixture verifies propagation of the compatibility gate. No production
guard was weakened to make that test pass. No live integrity claim is made.
