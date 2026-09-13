# Phase 7 Package 138 - Terminal-Series Isolation Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`f4e109ccb0c8b36c125e5dffff9322637fa284b9`.

This audit reads repository code, tests, and committed redacted package records
only. It does not read or mutate the private manifest, checkpoints, database,
cache, or runtime reports and does not contact Yahoo.

## Findings

`ResumableMarketBatchService` accepts checkpoint schema versions 1 and 2. Its
outcomes have only `SUCCESS`, `EMPTY`, or `FAILED`; only the first two are
skipped on resume. A `FAILED` outcome has an exception class name but no stable
failure category, attempt boundary, terminal decision, or evidence reference,
so every invocation retries it.

The one-batch service reports `PARTIAL` or `FAILED` whenever any outcome remains
`FAILED`. `ManifestBatchDrainService._is_complete` likewise accepts a batch
only when exact request coverage contains solely `SUCCESS` or `EMPTY`. It then
stops on every non-`SUCCESS` batch and rejects any later checkpoint as
out-of-order. Therefore simply executing batch 42 cannot bypass batch 41, and
treating every existing `FAILED` as complete would silently suppress transient,
rate-limit, transport, and unknown failures.

The checkpoint diagnostic and failed-series diagnostic also recognize only the
three current statuses. The latter deliberately selects exactly one `FAILED`
outcome. These are direct consumers of any checkpoint version change.

`ProjectedHistoricalMarketService` performs complete strict projection before
calling `CandleRepository.save_many`. Consequently the rejected batch-41
series did not pass the repository boundary and its invalid values were not
partially stored by that failed attempt.

Package 136 binds a normal-path `REJECTED/RESPONSE_NUMERIC` result to batch 41.
Package 137 binds an explicit repaired-path result to the same manifest,
request, window, and single failed candidate. Yfinance marked one row as
repaired, but strict projection still returned
`REJECTED/RESPONSE_NUMERIC`. These two reports justify isolation for this fixed
manifest; neither justifies modifying or persisting a candle.

## Rejected shortcuts

- Do not reinterpret all legacy `FAILED` outcomes as terminal.
- Do not manually edit the private checkpoint or maintain an unbound symbol
  skip list.
- Do not treat a redacted report alone as authority without verifying its raw
  SHA-256 and exact manifest/request/window bindings.
- Do not delete the interior row, invent OHLC values, weaken `Candle`
  validation, or persist the rejected repaired frame.
- Do not allow rate limits, timeouts, transport failures, unknown exceptions,
  or `NO_PRICE_DATA` to enter this first isolation policy.

## Selected versioned boundary

Implement one evidence-bound terminal-series isolation vertical slice next.
It must be reusable for later deterministic candle-value defects and must not
contain batch-41 symbols or private values in code.

1. Add a manifest-bound isolation service and CLI which accept the exact
   private manifest/checkpoint plus the normal diagnostic and repaired
   qualification files and caller-supplied SHA-256 values.
2. Before any write, validate all four manifest checksum, batch index, request
   checksum, and requested-window bindings; exact checkpoint request coverage;
   exactly one retryable `FAILED` outcome; normal and repaired strict rejection
   with the same allowlisted category; and strict JSON/report schemas.
3. Policy version 1 permits only `RESPONSE_NUMERIC` or `RESPONSE_OHLC` after
   both normal and explicit repaired projection reject the same fixed series.
   Other categories remain retryable and fail closed.
4. Atomically migrate the checkpoint to schema version 3 and change only the
   selected outcome to `FINAL_FAILED`. Preserve its original failure type and
   add stable failure category, policy identity, and both evidence SHA-256
   values. The same transition with the same evidence must be idempotent;
   conflicting evidence must fail before a write.
5. Emit a separate redacted schema-version-1 isolation report with exact
   manifest/request binding, aggregate transition counts, policy/category, and
   evidence checksums. It must exclude symbol, currency, prices, paths, and
   provider or exception text.
6. Version the resumable batch report to schema 4 and its manifest envelope to
   schema 3. A request with no retryable failures and one or more
   `FINAL_FAILED` outcomes reports `SUCCESS_WITH_EXCLUSIONS`, exposes separate
   retryable and final failure counts, and makes zero provider calls for final
   outcomes. Existing schema-1/2 checkpoints remain readable.
7. Version the drain report to schema 3. `_is_complete` accepts exact coverage
   containing `SUCCESS`, `EMPTY`, or `FINAL_FAILED`; the coordinator advances
   on `SUCCESS_WITH_EXCLUSIONS`; starting/current/ending coverage exposes final
   failure totals and categories. Existing out-of-order, checksum, budget,
   atomic-write, and stop-on-retryable-failure guards remain unchanged.
8. Version the checkpoint diagnostic to schema 2 so final failures are counted
   separately. Failed-series and repaired-series diagnostics continue to
   select only retryable `FAILED` outcomes and cannot reopen `FINAL_FAILED`.

The implementation must add success, idempotency, mismatch, unsupported-
category, failed-write, legacy migration, provider-bypass, aggregation,
out-of-order, CLI privacy, and architecture tests. It must not contact Yahoo,
run batch 41 or 42, or mutate private evidence. After implementation, one
controlled isolation transition for the already measured batch-41 evidence is
the next operational gate.

## Architectural effect

This is a versioned operations/checkpoint/report change. It does not change the
`Candle` model, SQLite schema, repository uniqueness, source manifest, or
analysis contracts. `FINAL_FAILED` means excluded from this fixed manifest run,
not permanently invalid across future manifests or refresh windows.

## Verification

- focused resumable batch, manifest execution/drain, diagnostics, persistence,
  and architecture tests: 95 passed, 2 skipped;
- complete suite: 3,036 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
