# Phase 7 Package 101 — Bounded Manifest-Drain Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`749c2d6a2c582583fcdddc8c2bce5f86fdc9e6ae`.

## Result

The existing one-batch manifest-bound executor, request checkpoint, and earlier
drain-coordinator patterns are sufficient foundations. A separate coordinator
is required; repeating 600 manual commands or adding a loop to the CLI is not a
safe operational contract.

Progress must derive only from checksum-valid private per-batch checkpoints.
SQLite candle presence cannot identify which manifest request completed, and a
redacted report cannot reconstruct private item outcomes. A batch is complete
only when its checkpoint matches the embedded request checksum, accounts for
every request symbol, and every outcome is terminal `SUCCESS` or `EMPTY`.

## Selected boundary

The next package should implement a separate manifest-drain service and CLI
that:

1. validates the private manifest identity and caller-supplied checksum once,
   before database or provider composition;
2. validates existing checkpoints in ascending batch-index order and selects
   the first unfinished batch deterministically;
3. owns deterministic private checkpoint names `batch_####.json` under one
   explicit checkpoint directory;
4. executes one request at a time through the existing manifest-bound service
   and carries each atomic checkpoint forward;
5. accepts an explicit `max_batches` budget from 1 through 25 and never treats
   the total manifest size as implicit authorization;
6. stops on manifest completion, budget exhaustion, zero progress, checkpoint
   mismatch, or the first `PARTIAL`/`FAILED` batch;
7. writes one redacted aggregate report containing manifest checksum, budget,
   starting/ending completed counts, attempted batch/item counts, transfer
   totals, stopping status/index, and privacy limitations.

`EMPTY` is an existing successful terminal request outcome and may advance the
coordinator. A prior `FAILED` item remains retryable through the unchanged
request service, but each coordinator invocation may run its batch only once.
The first non-success result stops the run, preventing a failure from expanding
into later requests.

## Known limitation

The current one-request service exposes exception class names but not the typed
Yahoo rate-limit classification used by eligibility and currency scanning. The
coordinator can still stop on the first non-`SUCCESS` batch, but that stop may
occur after the remaining items of the same at-most-20-item request were tried.
This is bounded and must remain explicit in its report. It is not sufficient
authority for an unbounded or scheduled drain.

## First operational bound

After implementation, the first controlled run should set `max_batches=5`.
With batch 1 already complete, it may attempt only batches 2–6. Review its
redacted report before increasing the budget. This audit does not read private
checkpoints or SQLite, contact Yahoo, execute batch 2, or authorize all 601
requests.
