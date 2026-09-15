# Phase 7 Package 149 — Sweep Failure Evidence Audit

## Classification

`AUDIT`

## Verified Baseline

```text
develop @ 76aa06c14b0800ac8b971ff21183d0c65e6f248a
```

## Scope

This audit reviewed repository code, tests, and committed redacted Package 148
evidence. It did not read or modify the private manifest, batch-106 checkpoint,
database, cache, symbols, currencies, candles, or provider response and did not
contact Yahoo.

## Findings

The collection sweep's safety boundary behaved correctly. A non-deferable
`APIError` was atomically checkpointed and re-raised before the next item. The
sweep then returned `HALTED`, did not execute batch 107, and did not count the
partial batch 106 as sweep-covered. Operator-reported SQLite integrity is `ok`.

The schema-version-1 report has one isolated aggregation defect:
`current_run.deferred_failure_count` counts every newly written `FAILED`
outcome. It must count only new outcomes whose status is `FAILED` and whose
failure type is exactly `YahooCandleInvalidResponseError`. Ending coverage
already applies that exact rule. Correcting this field to zero for the Package
148 shape is a backward-compatible bug fix, not a schema migration.

The persisted causal-evidence gap is separate. `YahooFinanceClient` preserves
the original yfinance or transport exception as the cause of its `APIError`.
`project_yahoo_candle_failure` can already produce a stable category and a
bounded, allowlisted, message-free exception type chain while that exception is
in memory. `ResumableMarketBatchService`, however, stores only
`type(exc).__name__`. Checkpoint schemas 1–3 therefore retain only `APIError`
for this failure. The original batch-106 cause cannot be recovered from the
checkpoint or redacted report.

The existing manifest failed-series raw diagnostic and repaired qualification
cannot be reused unchanged. Their common selector requires exact coverage of
all request items and exactly one failed outcome. Batch 106 is intentionally a
partial checkpoint. Relaxing that exact-coverage contract would change the
meaning of established diagnostics, and repair mode is not justified for a
request-layer `APIError`.

## Selected Smallest Boundary

Implement one separate read-only manifest partial-failure qualification plus
the isolated counter correction.

1. Validate the complete manifest, selected batch, request checksum, and the
   existing partial checkpoint before provider composition.
2. Require checkpoint outcome keys to be an exact subset of request symbols,
   exactly one `FAILED` outcome, and that failure type to be `APIError`.
   Successful, empty, final, or deferred local-validation evidence remains
   unchanged and no missing item may be selected accidentally.
3. Internally select the one failed private item and make exactly one
   production-path Yahoo projection request over the manifest's original
   resolution, currency, and half-open ten-year window.
4. Do not open SQLite and do not write the checkpoint. A returned projection
   emits only `QUALIFIED` or `EMPTY`, aggregate candle count, and bounded
   omission evidence. A raised exception emits the existing stable Yahoo
   failure category and allowlisted exception type chain.
5. Emit a separate versioned report with manifest/batch/request bindings and no
   identity, currency, price, path, provider text, exception message, raw row,
   or candle value.
6. Correct the existing sweep current-run deferred counter to include only the
   exact deferable type. Add the Package-148 systemic-halt regression shape.
7. Keep checkpoint schema 3 and every existing drain/diagnostic contract
   unchanged in this package.

## Future Failure Evidence

The selected qualification measures whether the exact production path is
currently usable; it does not reconstruct the lost original cause and does not
authorize retry. After its operational result is reviewed, a later versioned
checkpoint package must decide whether to persist category/type-chain evidence
at failure time before broad sweep resume. Retrofitting guessed evidence into
the current private checkpoint is forbidden.

## Rejected Shortcuts

- Do not infer rate limiting, transport failure, missing price data, or invalid
  response from the generic stored `APIError` string.
- Do not rerun the sweep: its blocking guard will stop without new provider
  work.
- Do not manually remove or rewrite the batch-106 failed outcome.
- Do not weaken exact coverage in the existing raw or repaired diagnostics.
- Do not count all retryable failures as deferred candle defects.
- Do not add automatic retries, scheduling, analysis, or trading authority.

## Verification

- focused sweep/resume/Yahoo/diagnostic/architecture tests: 103 passed;
- complete suite and whitespace verification are required for this audit
  package handoff.

## Next Package

Implement the selected read-only partial-failure qualification and exact
deferred-counter correction. Do not contact Yahoo or retry batch 106 until that
implementation and its failure paths pass review.
