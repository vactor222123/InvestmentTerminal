# Phase 7 Package 147 — Manifest Collection Sweep

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ 0e9dcd9f79da64ffaa289c8bd017b69beb93d9a5
```

## Result

Package 147 implements the separate collection boundary selected by Package
146. It does not relax or replace the existing ordered fail-fast manifest
drain.

`ManifestCollectionSweepPlan` validates the complete manifest and a caller-
owned batch budget before runtime composition. The budget may cover from one
batch through the complete manifest. `ManifestCollectionSweepService` derives
attempted coverage only from exact request-checksum-bound private checkpoints.

A batch is sweep-covered only when every requested identity has an outcome and
every retryable failure is exactly `YahooCandleInvalidResponseError`. Existing
failed outcomes are preserved and not retried during collection. Missing items
in an interrupted batch are still processed.

The resumable executor now exposes two optional execution policies. Their
defaults preserve every existing caller: failed outcomes remain retryable and
item failures remain isolated. The sweep explicitly disables retry of existing
failures and continues after only the exact local Yahoo candle-validation
class. Every other importer failure is atomically checkpointed and immediately
halts the sweep before the next item or batch. A checkpoint-write failure is
not treated as durable progress and propagates to the failed CLI envelope.

## Report Contract

The schema-version-1 `MANIFEST_COLLECTION_SWEEP` report distinguishes:

- `sweep_covered_batch_count`: complete attempted request coverage, including
  an allowed deferred local candle defect;
- `fully_complete_batch_count`: covered batches with no retryable failure;
- `remaining_unswept_batch_count`;
- aggregate deferred failure counts and the single allowed type;
- current attempted batch/item and transfer/duplicate/omission totals;
- a stopping batch index and non-deferable failure types.

The report contains no symbols, currencies, prices, paths, provider payload or
exception messages. `COMPLETE` means collection-attempt coverage, not that all
series succeeded. Deferred failures remain private checkpoint evidence for a
later remediation pass.

## Failure Boundaries

- Only the exact `YahooCandleInvalidResponseError` type is deferable.
- Subclasses and generic `APIError`, timeout, transport, rate-limit,
  persistence, checkpoint, and unknown failures do not advance collection.
- Out-of-order or checksum-invalid checkpoints fail before provider access.
- Existing `ManifestBatchDrainService` ordering and retry semantics are
  unchanged.
- No scheduler, repair, final-failure transition, analytical conclusion, or
  trading action is added.

## Verification

Focused tests cover exact prior-defect resume, newly deferred local defects,
immediate systemic halt inside a request, interrupted partial resume, invalid
execution policy, checkpoint ordering, writer failure, completed resume,
privacy, CLI preflight failure, and unchanged manifest/resumable behavior.

## Next Gate

Run one user-executed collection sweep against the established private
manifest, checkpoint directory, database, and cache. Use the full remaining
budget only after confirming the expected baseline and command inputs. With
the recorded checkpoint state, batches through 105 are sweep-covered and batch
106 is the expected first provider batch. Return only the redacted sweep report
and a separately computed read-only SQLite integrity result.
