# Phase 7 Package 133 - Manifest-Drain Restart Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`6687c7221400ea141b5393de4a45ca2837f1a465`.

## Finding

The existing manifest-drain boundary remains sufficient after batch-19
recovery. `ManifestBatchDrainPlan` validates the complete manifest and every
embedded request checksum and enforces an explicit budget from one through 25
batches. The service reads deterministic `batch_####.json` checkpoints in
ascending order and derives completion only from a matching request checksum,
exact request-symbol coverage, and terminal `SUCCESS` or `EMPTY` outcomes.
SQLite candle presence is not used as a completion index.

All checkpoints are inspected before the first importer call. A checkpoint
after the first unfinished batch is rejected as out-of-order. The coordinator
then executes only the first unfinished batch, carries forward its existing
atomic checkpoint, and advances sequentially. It stops on manifest completion,
budget exhaustion, or the first `PARTIAL`/`FAILED` batch. One failed batch can
attempt at most its existing 20-item request; no later batch is reached.

The schema-version-2 drain report already separates starting, current-run, and
ending coverage and includes attempted batch/item counts, transfer totals,
typed omission totals, stop index, and failure types. `COMPLETE` and
`BUDGET_EXHAUSTED` are successful CLI exits; `HALTED` and preflight failures
exit nonzero. No contract or implementation change is required.

## Measured restart basis

The reviewed redacted evidence establishes batches 1–18 as complete before the
halt and Package 132 establishes batch 19 as 20/20 successful with SQLite
integrity `ok`. Therefore, provided the unchanged private checkpoint directory
passes the coordinator's own validation and contains no later progress, the
first unfinished index is 20.

This audit does not read the private manifest, checkpoints, database, or cache,
and it does not contact Yahoo. The operational command must validate those
private prerequisites locally before execution rather than infer them from
SQLite or recreate checkpoints.

## Selected operation

Authorize one existing `max_batches=25` drain invocation. It may begin only at
batch 20 and may reach at most batch 44. It must stop on the first non-success
batch and return only its redacted aggregate report plus a privacy-safe SQLite
integrity result. Review that evidence before any further invocation.

The known bounded limitation remains: provider rate limiting is not classified
inside a manifest request, so the current request may finish attempting its
remaining items before the coordinator halts. The 20-item request cap and
stop-before-next-batch rule bound that exposure. Scheduling, an unbounded drain,
repaired retrieval, batch 45, analysis, and trading remain out of scope.

## Verification

- focused drain, manifest execution, checkpoint, projection, and architecture
  tests: 41 passed;
- complete suite: 3,036 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
