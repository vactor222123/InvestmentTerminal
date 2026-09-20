# Phase 7 Package 164 — Batch-576 Timeout Retry Audit

## Classification

`AUDIT`

## Verified Baseline

```text
develop @ b0d2f28156ceee9b05d7f0be8711540ecba2ca03
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-1
`MANIFEST_PARTIAL_CAUSAL_INVENTORY` report was reviewed. No private manifest,
checkpoint, database, cache, symbol, currency, price, or candle was read.

Report SHA-256:

```text
67fd4eca4ede8205c5e669a44d70cbd269601227c7a939b80b5776d29d35e069
```

The report is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 576 of 601, and request checksum
`0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb`.
Its 18 stored outcomes reconcile as 15 successes and three retryable failures,
with two request members still missing.

The three causal signatures are exact and non-overlapping:

- one blocking `TIMEOUT` with chain `APIError -> curl_cffi Timeout -> CurlError`;
- one deferable `NO_PRICE_DATA` with chain
  `APIError -> YFPricesMissingError`;
- one deferable `RESPONSE_OHLC` local candle-validation failure.

The prior SQLite integrity result remains `UNVERIFIED`; the inventory neither
opens SQLite nor establishes corruption.

## Audit Finding

The blocking outcome is a transient transport timeout, not a candle defect and
not missing-price evidence. It must not be terminalized or made deferable.

Repeating the collection sweep is ineffective: checkpoint validation sees the
stored blocking outcome before composing the provider and halts without a Yahoo
request. Running the general manifest-bound batch retry is also too broad: its
default retry behavior would repeat all three `FAILED` outcomes, including the
two already classified as deferable.

The existing partial-failure qualification cannot select the timeout because it
requires exactly one failed outcome. The aggregate inventory supplies enough
evidence to select the unique timeout signature internally without revealing a
private identity, but it has deliberately no retry or checkpoint-write
authority.

## Selected Next Boundary

Implement a separate manifest-bound partial-timeout retry operation. It must:

- validate the exact manifest, batch, request, proper-partial schema-4
  checkpoint, and immutable causal-inventory bytes/checksum before provider
  access;
- require exactly one blocking `TIMEOUT` signature and select only the one
  private outcome whose stored causal evidence equals that signature;
- make at most one production-path retry and leave the stored `NO_PRICE_DATA`,
  `RESPONSE_OHLC`, successes, and missing members untouched;
- atomically replace only the selected outcome with the retry result while
  preserving schema-4 causal evidence for any new failure;
- emit a separate redacted aggregate report before any collection resume;
- keep repeated timeout, rate-limit, transport, persistence, checkpoint, and
  unknown failures blocking.

This is a reusable typed-timeout recovery boundary for later batches, not a
batch-576 symbol exception. It does not add automatic retry loops, sleeps,
timeout deferral, or terminal exclusion.

## Scope Exclusions

- no Yahoo request or private checkpoint mutation in this audit;
- no collection-sweep resume or execution of batches 577–601;
- no retry of either deferable outcome;
- no SQLite access, candle persistence, analysis, or trading authority;
- no inference from the absent SQLite integrity line.

## Verification

```text
focused sweep, causal-inventory, CLI, architecture, and documentation tests:
41 passed in 3.06s
full test suite: 3135 passed, 4 skipped, 1 warning in 35.72s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 164 regression.

## Next Package

Implement the evidence-bound one-time partial timeout retry with focused
success, repeated-timeout, rate-limit, ambiguous-selection, evidence-mismatch,
checkpoint-write, privacy, CLI, and architecture tests. Do not resume the sweep
until the redacted retry result is reviewed.
