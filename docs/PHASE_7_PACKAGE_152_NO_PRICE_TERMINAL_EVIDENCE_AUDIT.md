# Phase 7 Package 152 — No-Price Terminal Evidence Audit

## Classification

`AUDIT`

## Verified Baseline

```text
develop @ ae51a17749bf56ec1a43585c2301beddfc69adde
```

## Scope

This audit reviewed repository contracts, checkpoint consumers, tests, and the
committed Package 151 redacted evidence record. It did not read or modify the
private manifest, checkpoint, cache, database, symbols, currencies, prices, or
provider response and did not contact Yahoo.

## Findings

The Package 151 result is sufficient current evidence for a separate no-price
terminal policy, but it is not the missing cause of the original batch-106
failure. The immutable report bytes are bound to the exact manifest, batch,
request, half-open window, proper partial checkpoint counts, one stored
`APIError`, and a current `NO_PRICE_DATA` projection whose allowlisted chain is
`APIError -> YFPricesMissingError`.

Checkpoint schema 3 cannot represent that policy safely. Its `FINAL_FAILED`
shape accepts only policy `NORMAL_AND_REPAIRED_STRICT_REJECTION_V1`, categories
`RESPONSE_NUMERIC` and `RESPONSE_OHLC`, and two strict-projection evidence
checksums. The owning service also requires complete request coverage. Those
guards are correct and must remain unchanged.

`ResumableMarketBatchService` is the point where causal evidence is lost. It
receives the complete in-memory exception but stores only its outer class name.
Every checkpoint consumer delegates parsing to its `_outcomes` boundary. The
collection sweep, bounded drain, manifest executor, checkpoint diagnostic, and
terminal-isolation services therefore share one viable versioned migration
seam. Existing aggregate reports already understand final failure categories
and do not need a shape change for this remediation.

## Selected Contract

Implement private resumable checkpoint schema version 4 and one separate
offline manifest-bound transition.

1. Schemas 1–3 remain readable and retain their exact meanings. Schema 4 keeps
   all existing outcome fields.
2. A schema-4 retryable `FAILED` outcome additionally owns
   `causal_failure_evidence`: either null for explicitly migrated legacy
   evidence or an object containing the existing stable Yahoo category and
   bounded allowlisted `exception_type_chain`.
3. Every newly caught importer failure must store the object produced by
   `project_yahoo_candle_failure` before the atomic checkpoint write. Messages,
   arguments, tracebacks, paths, identities, and provider payloads remain
   forbidden. Public report shapes remain unchanged.
4. A separate `REPRODUCED_YAHOO_NO_PRICE_DATA_V1` transition verifies strict
   UTF-8 JSON report bytes against a caller-supplied SHA-256 before checkpoint
   mutation. It accepts only the exact Package-150 qualification identity,
   manifest/request/window bindings, proper partial selection counts, stored
   `APIError`, `FAILED/NO_PRICE_DATA`, null coverage, and an allowlisted chain
   beginning with `APIError` and containing a recognized yfinance missing-price
   exception.
5. The transition changes only that one private outcome to `FINAL_FAILED`,
   retains outer `failure_type=APIError`, records category `NO_PRICE_DATA`, the
   new policy identity, and
   `partial_failure_qualification_checksum`. Existing outcomes and all missing
   request items remain untouched.
6. Exact repeat with matching final evidence is idempotent. Conflicting final
   evidence, complete or empty checkpoints, another category/type chain,
   mismatched counts/bindings/checksum, duplicate JSON keys, non-finite JSON,
   or unsupported schemas fail before write.
7. The CLI writes the private checkpoint atomically before the separate
   redacted schema-version-1 transition report. Checkpoint-write failure cannot
   claim success; report-write failure after commit is reconciled by exact
   idempotent repeat.

After a successful transition, the unchanged collection sweep may skip the
terminal item and attempt only the 13 missing batch-106 members. Any new
failure will retain privacy-safe causal evidence at failure time. This package
does not authorize that transition or sweep execution.

## Consumer Impact

- `ResumableMarketBatchService._outcomes` becomes the schema-4 validation owner.
- New checkpoint writes use schema 4; read-only/exact resume does not rewrite a
  legacy checkpoint merely to migrate it.
- Existing schema-3 numeric/OHLC terminal isolation remains valid and separate.
- `ManifestCollectionSweepService` continues to block retryable non-local
  failures and treats a valid final exclusion as terminal.
- `ManifestBatchDrainService` and checkpoint diagnostic already aggregate
  final category evidence without public JSON changes.
- Manifest request, `Candle`, SQLite, omission, and existing report schemas do
  not change.

## Rejected Shortcuts

- Do not overwrite the old `APIError` with the currently observed cause.
- Do not add `NO_PRICE_DATA` to the existing strict-rejection policy.
- Do not reuse repaired-series evidence for an absent provider series.
- Do not treat generic `APIError`, empty projection, timeout, rate limit, or
  provider failure as terminal no-price evidence.
- Do not put exception messages or private identities in checkpoints/reports.
- Do not resume the sweep in the implementation package.

## Next Package

Implement the selected schema-4 causal evidence and evidence-bound no-price
transition with focused migration, privacy, idempotency, conflict, atomic-write,
and future-failure tests. Do not contact Yahoo or modify runtime evidence. A
separate operational package must perform the transition after implementation
review.
