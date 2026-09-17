# Phase 7 Package 161 — Causal No-Price Sweep Deferral

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ 2df941adaa4d4a418f591a58c14c0396711547b9
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-1
`MANIFEST_STORED_NO_PRICE_ISOLATION` report was reviewed. No private manifest,
checkpoint, database, cache, symbol, currency, price, or candle was read.

Report SHA-256:

```text
80370a101725f22ea582b9d68d4e06d3c77b0b6c2f272f33e67bdfae2cd4ae13
```

The report is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 109 of 601, request checksum
`a3b00484a202f114f2051f0568f1ed61c0d79535415266ebba120c15134c0a34`,
and diagnostic checksum
`509769c10ef7a4617104b80c5ed3ca626cd763e98c97e76353d52586507b64ef`.
It records one transitioned and cumulative final `NO_PRICE_DATA` exclusion,
zero retryable failures, and 19 missing request members.

## Optimization

The collection sweep previously deferred only exact local
`YahooCandleInvalidResponseError`. Every `APIError` halted all later collection,
even when a schema-4 checkpoint preserved the same validated missing-price
causal evidence already accepted by Package 159. That would repeat the manual
diagnostic/transition cycle for every equivalent unavailable series.

Package 161 keeps the evidence boundary but removes that collection bottleneck:

- exact local Yahoo candle-validation defects remain deferable;
- exact outer `APIError` becomes deferable only when the causal category is
  `NO_PRICE_DATA`, the chain starts with InvestmentTerminal `APIError`, contains
  a recognized yfinance missing-price type, and has no redaction or truncation;
- the same predicate validates newly raised in-memory evidence and persisted
  schema-4 checkpoint evidence;
- existing deferred outcomes are never retried during the collection sweep;
- the sweep does not automatically terminalize, repair, or infer a price;
- legacy/null, generic, redacted, truncated, timeout, transport, rate-limit,
  persistence, checkpoint, and unknown failures remain blocking.

The `MANIFEST_COLLECTION_SWEEP` report advances to schema version 2. It
preserves the schema-1 shape and statuses while versioning the expanded sorted
`deferred_failure_types` vocabulary. This lets collection finish before one
aggregate failure-inventory and remediation pass.

## Failure-Path Coverage

Focused tests cover new in-memory no-price deferral, exact resume over persisted
schema-4 no-price evidence, continued later-batch collection, generic/legacy,
timeout, rate-limit, redacted, and non-no-price blocking behavior, existing
local-defect deferral, checkpoint ordering, writer failure, CLI preflight, and
architecture guards.

## Scope Exclusions

- no private runtime mutation or provider request in this package;
- no automatic terminal transition, retry, price inference, or candle repair;
- no relaxation for rate limiting, transport, timeout, database, or checkpoint
  failure;
- no aggregate remediation implementation yet;
- no analysis or trading authority.

## Verification

Focused regression:

```text
144 passed in 4.25s
```

Full regression:

```text
3127 passed, 4 skipped, 1 warning in 31.99s
```

The warning is the pre-existing Starlette `httpx` deprecation warning. The
repository diff check passed.

## Next Package

Prepare one exact-baseline ASCII-only PowerShell handoff for the existing
collection sweep with the complete remaining batch budget. It must validate the
transitioned batch-109 checkpoint, schema-version-2 redacted report, and
read-only SQLite integrity. Return only the report and integrity result. After
complete collection, build one aggregate deferred-failure inventory instead of
processing each series manually.
