# Phase 7 Package 163 — Partial Causal Inventory

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ 1f5685957814194adca12f882b94b9b18ed8c666
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-2
`MANIFEST_COLLECTION_SWEEP` report was reviewed. No private manifest,
checkpoint, database, cache, symbol, currency, price, or candle was read.

Report SHA-256:

```text
356feed607a4d8a235757818718c443caf3b42f85b5d8bd82d2727b4ff9bfee2
```

The report is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`.
It started with 108 covered batches, processed 9,357 items across 468 attempted
batches, and halted safely at batch 576 after 4,101.893697 seconds. It inserted
13,640,007 of 13,660,063 downloaded candles and reconciled 20,056 duplicates.
Coverage reached batch 575; 26 batches remain.

The separately requested SQLite integrity line was not returned. Integrity is
therefore `UNVERIFIED`, not failed or corrupt.

## Audit Finding

Ending covered evidence contains 118 deferred failures, while the run counted
119 newly deferred outcomes after starting with one. The exact accounting means
117 new deferred outcomes are in newly covered batches and two more are already
stored inside uncovered stopping batch 576. The same partial batch also has at
least one blocking `APIError`, because that exact type halted the sweep.

The existing single-failure causal diagnostic deliberately requires exactly one
retryable failure. It cannot select the blocking outcome safely when multiple
private outcomes share the same outer failure type. Repeating Yahoo or sending
the private checkpoint would discard or expose the causal evidence already
stored by checkpoint schema 4.

## Implementation

`ManifestPartialCausalInventoryDiagnostic` validates one checksum-bound proper
partial checkpoint through the existing manifest and checkpoint parsers. It
groups all retryable failures by stable causal category, complete
allowlisted exception-type chain, and the collection sweep's exact
`DEFERABLE`/`BLOCKING` predicate. The schema-version-1 redacted report contains
only aggregate coverage, signature counts, and bindings. The private outer
`failure_type` is used for classification but is not copied to the report.

The CLI reads only the supplied private manifest and checkpoint, then atomically
writes the detached report. It has no Yahoo client, cache, SQLite, repository,
importer, checkpoint writer, retry, terminal transition, or later-batch
authority. Null legacy evidence remains explicit and blocking. Unsupported,
malformed, complete, empty, out-of-request, or no-failure checkpoints fail
closed with a redacted report.

## Privacy Boundary

The report excludes symbols, currencies, prices, paths, outer failure-type
strings, provider text,
exception messages, candle values, and raw rows. Exception type names have
already passed the existing schema-4 allowlist and bounded-chain validator.
Counts and causal signatures cannot be used to identify a private member.

## Verification

```text
focused causal-inventory, causal-evidence, sweep, checkpoint, and architecture tests: 88 passed in 3.33s
full test suite: 3135 passed, 4 skipped, 1 warning in 26.87s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 163 regression.

## Next Package

Prepare one exact-baseline ASCII-only PowerShell handoff for batch 576. It must
locate the unique request-bound private checkpoint, run only the new offline
inventory, validate the redacted report, and print explicit `SEND` and
`DO NOT SEND` paths. Do not resume the sweep until the blocking causal signature
is reviewed.
