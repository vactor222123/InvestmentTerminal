# Phase 7 Package 156 — Stored Causal Evidence Diagnostic

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ b811978b9413bf3b3c21716531c234141df811b5
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-1
`MANIFEST_COLLECTION_SWEEP` report was reviewed. The private manifest,
checkpoints, database, cache, symbols, currencies, prices, and candles were not
reviewed.

Report SHA-256:

```text
7f069958b4e5a95ca5f2002e1e43b8d5991c2feccd4dcb4f8be81648063b99c7
```

The report is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`.
It records `HALTED` after 21.80134 seconds:

```text
starting sweep-covered batches = 105
ending sweep-covered batches = 108
starting remaining batches = 496
ending remaining batches = 493
attempted batches = 4
attempted items = 54
downloaded candles = 79735
inserted candles = 79735
duplicates = 0
trailing omissions = 0
stop batch = 109
failure types = APIError
```

The prior deferred `YahooCandleInvalidResponseError` remains explicit and was
not changed. The operation behaved as designed: completed work survived and a
systemic failure stopped progress before batch 110.

## Audit Finding

Unlike the legacy batch-106 failure, the batch-109 failure was written by the
schema-version-4 checkpoint path. `ResumableMarketBatchService` therefore
stored either validated privacy-safe causal evidence or an explicit null legacy
marker before the sweep halted. Repeating Yahoo qualification before inspecting
that evidence would discard the principal benefit of schema 4.

The sweep report intentionally cannot reveal the category or type chain. The
existing checkpoint diagnostic exposes only aggregate failure types, while the
existing partial-failure qualification performs another provider request.
Neither is the correct boundary for this case.

## Implementation

`ManifestPartialCausalEvidenceDiagnostic` validates exact manifest, request,
proper-partial checkpoint, and one-`APIError` selection semantics by reusing the
existing parsers. It then emits one detached redacted report:

- `EVIDENCE_AVAILABLE` carries only the stored stable category and allowlisted
  exception-type chain;
- `LEGACY_EVIDENCE_UNAVAILABLE` carries null evidence and makes no inference;
- `FAILED` records only a stable local exception class and fixed reason.

The CLI reads only the supplied manifest and checkpoint and atomically writes
the report. It has no Yahoo client, cache, SQLite, repository, importer,
checkpoint writer, candle persistence, remediation, or later-batch authority.
Symbols, currencies, prices, paths, provider text, exception messages, raw
rows, and candle values are excluded.

## Repository Verification

```text
focused tests and architecture guards: 56 passed in 2.88s
full test suite: 3102 passed, 4 skipped, 1 warning in 28.57s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 156 regression.

## Next Gate

After this package is applied, prepare one exact-baseline user-executed offline
diagnostic for batch 109. Return only its redacted report. Do not contact Yahoo,
open SQLite, mutate the checkpoint, resume batch 109, or execute batch 110
until the stored causal evidence is reviewed.
