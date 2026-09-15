# Phase 7 Package 146 — Complete Collection Sweep Audit

## Classification

`AUDIT`

## Verified Baseline

```text
develop @ e603e510d13044deef7430ec58f21a5ce9052881
```

## Scope

This audit reviewed repository code, tests, and committed redacted package
records only. It did not read or modify the private manifest, checkpoints,
database, cache, or candle evidence and did not contact Yahoo.

## Findings

`ManifestBatchDrainService` defines progress as a contiguous prefix of exact
request checkpoints containing only `SUCCESS`, `EMPTY`, or `FINAL_FAILED`. It
stops on the first `PARTIAL` or `FAILED` batch and rejects every later
checkpoint as out-of-order. This is correct for fail-fast remediation but means
the one retryable failure in batch 105 blocks batches 106–601.

`ResumableMarketBatchService` atomically checkpoints after every attempted
item. On resume it skips successful, empty, and final outcomes but retries every
`FAILED` outcome. It also catches every importer exception and stores only its
class name. The checkpoint therefore does not distinguish a local candle-frame
defect from rate limiting, provider transport, SQLite persistence, or another
systemic failure.

The exact `YahooCandleInvalidResponseError` class is nevertheless a safe first
deferable boundary. The production Yahoo client raises it only while projecting
the returned frame, before `ProjectedHistoricalMarketService` calls
`CandleRepository.save_many`. Other Yahoo request failures are wrapped in
`APIError`; persistence errors retain their non-Yahoo class. Allowing arbitrary
`FAILED`, `APIError`, timeout, transport, or unknown outcomes to advance would
be unsafe.

The current checkpoint set already contains sufficient private authority for a
separate sweep: exact request checksum plus complete requested-symbol coverage
proves every item in a batch was attempted. SQLite rows and redacted reports do
not prove that fact. No separate symbol skip list should be introduced.

## Selected Boundary

Implement a separate `ManifestCollectionSweepPlan`, service, and CLI. Do not
change the existing manifest drain's behavior or report.

1. Validate the complete manifest and every private checkpoint before provider
   or database composition.
2. Define a sweep-covered batch as exact request-symbol coverage whose outcomes
   are `SUCCESS`, `EMPTY`, `FINAL_FAILED`, or retryable `FAILED` with the exact
   type `YahooCandleInvalidResponseError`.
3. Select the first batch without sweep coverage. Existing batch 105 is thereby
   preserved without retry, and the first operational candidate is batch 106.
4. Add an explicit non-retry execution mode to the existing resumable batch
   boundary: already present `FAILED` outcomes are skipped, while missing items
   remain executable. The default retry behavior remains unchanged for every
   existing caller.
5. During a sweep, checkpoint every attempted item atomically. Continue after
   an exact `YahooCandleInvalidResponseError`; stop processing and halt before
   the next batch for every other exception or failure type.
6. A provider or persistence failure may affect only the current request's
   bounded remainder. The implementation should stop immediately within that
   request when the failure is not deferable rather than attempt its remaining
   items.
7. Use a caller-owned batch budget bounded by the 601-request manifest. Exact
   resume derives from checkpoint coverage and performs no provider work for
   already swept batches.
8. Emit a new redacted versioned `MANIFEST_COLLECTION_SWEEP` report. Separate
   sweep-covered batches, fully complete batches, deferred failure counts/types,
   current transfer/duplicate/omission totals, stop index, and systemic failure
   evidence. Never expose identities, currencies, paths, prices, provider text,
   or exception messages.
9. Treat `COMPLETE`, `BUDGET_EXHAUSTED`, `HALTED`, and preflight `FAILED` as
   distinct outcomes. A complete sweep means attempted coverage, not that every
   series succeeded.

## Failure and Resume Semantics

The sweep does not convert `FAILED` to `FINAL_FAILED`; deterministic terminal
isolation still requires its existing evidence-bound policy. Deferred outcomes
remain available for a later remediation pass. Because later checkpoints can
exist after an earlier deferred failure, the old fail-fast drain will correctly
reject that directory as out-of-order until failures are remediated in order.
This is expected and must be documented rather than weakened.

If execution is interrupted inside a batch, the non-retry mode must preserve
all existing outcomes, skip even prior retryable failures, and attempt only
missing request items. This avoids repeatedly contacting the same defective
series merely to resume collection.

## Rejected Shortcuts

- Do not mark all retryable failures final.
- Do not modify the private manifest or manually edit checkpoints.
- Do not infer attempted coverage from SQLite rows or report totals.
- Do not continue after generic `APIError`, rate limiting, timeout, transport,
  SQLite, checkpoint-write, or unknown failures.
- Do not remove the old drain's ordered fail-fast guard.
- Do not diagnose each deferred series before collecting later independent
  series.

## Verification Required for Implementation

Focused tests must cover the batch-105 resume shape, local-validation deferral,
immediate systemic halt, interrupted partial-batch resume without retry,
checkpoint mismatch, atomic write failure, exact completed resume, aggregate
privacy, budget boundaries, and unchanged legacy drain behavior. The complete
suite and `git diff --check` must pass.

Audit verification:

- focused resumable/manifest/drain/Yahoo/persistence/architecture tests:
  103 passed;
- complete suite: 3,050 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next Package

Implement the selected collection sweep without runtime access. Do not execute
batch 106 until that implementation and its failure paths are reviewed.
