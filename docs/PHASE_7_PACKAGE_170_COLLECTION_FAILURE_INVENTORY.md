# Phase 7 Package 170 — Collection Failure Inventory

## Classification

`IMPLEMENTATION — COMPLETE`

## Verified Baseline

```text
develop @ 46ecae73235492ba7479003b98b61f1800074222
```

## Reviewed Operational Evidence

The explicitly returned redacted schema-version-2 collection-sweep report has
SHA-256:

```text
b8e7504cd1a6ff8b5755ed60ffde9ff20bd70a32111ea845e624105ab65be0dc
```

It is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and reports `COMPLETE` with the exact 26-batch budget. Starting coverage was
575 batches with 26 remaining. The run attempted all 26 remaining batches and
501 items, downloaded and inserted 594,088 candles, recorded zero duplicates
and omissions, and ended with all 601 batches sweep-covered.

Ending evidence contains 495 fully complete batches, zero unswept batches, and
124 explicit deferable failures of the two supported types. The difference
between four current-run deferred outcomes and six newly visible ending
outcomes is consistent with batch 576 already containing two deferred outcomes
before its two missing members were processed. No stop batch or systemic
failure type is present.

The requested separate `SQLite integrity: ok` line was not returned with this
report, so database integrity remains unverified for this package. No private
manifest, checkpoint, database, cache, symbol, currency, price, or candle was
read.

## Implementation

`ManifestCollectionFailureInventoryService` is a read-only aggregate boundary
over the completed sweep. It requires strict sweep-report checksum and
manifest binding, valid ordered fully covered checkpoints, equality between
reported and checkpoint-derived ending coverage, and zero blocking failures.

Its schema-version-1 report counts complete checkpoint coverage and all outcome
statuses. Retryable failures are grouped by optional stored causal category and
allowlisted exception-type chain. Terminal exclusions are grouped by category
and isolation-policy identity. Null legacy causal evidence remains explicit.
The report contains no private identity or value.

The CLI atomically writes a separate redacted report. It has no Yahoo client,
cache, SQLite, repository, importer, checkpoint writer, retry, or terminalizing
dependency. Any checksum, coverage, ordering, or contract mismatch produces a
redacted `FAILED` report and a non-zero exit.

## Scope Exclusions

- no provider request or candle ingestion;
- no checkpoint or SQLite mutation;
- no automatic retry or terminal transition;
- no symbol-level export;
- no analysis, recommendation, scheduling, or trading authority;
- no claim that SQLite integrity is `ok` without separately returned evidence.

## Repository Verification

```text
focused inventory, sweep, partial-inventory, resumable-batch, manifest, and
architecture tests: 75 passed in 3.16s
full test suite: 3154 passed, 4 skipped, 1 warning in 27.53s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 170 regression.

## Next Package

Prepare one exact-baseline ASCII-only PowerShell handoff that runs the new
inventory once against the completed private checkpoint set, validates the
redacted report, and checks SQLite integrity read-only. Return only the
inventory report and the printed integrity result.
