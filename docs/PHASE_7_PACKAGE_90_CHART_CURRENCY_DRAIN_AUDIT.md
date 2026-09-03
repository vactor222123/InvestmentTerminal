# Phase 7 Package 90 — Complete Chart-Currency Drain Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`5c0910e043de1f5bbadc50e1ecd8ad1b35e396af`.

## Finding

The existing currency qualification service deliberately accepts only 1–100
items. It atomically checkpoints every outcome, resumes deterministic pending
order, caps attempts at three, and halts immediately on rate limiting. The CLI
runs exactly one slice. With 11,919 members remaining, manual repetition would
preserve correctness but create unnecessary operator and stopping risk.

`UniverseEligibilityDrainService` proves the appropriate coordination pattern,
but cannot be reused directly because eligibility and currency have different
request, status, coverage, provider, and checksum contracts. Raising the
currency slice cap is rejected because it would remove the reviewed boundary
without adding run-level control.

## Selected implementation

Add one separate operations-owned chart-currency drain coordinator and CLI.
They must:

- repeat the existing service in deterministic slices of at most 100;
- accept an explicit positive total-item budget capped at 20,000;
- carry forward the latest successfully written private checkpoint;
- stop on `COMPLETE`, `HALTED/RATE_LIMITED`, budget exhaustion, zero progress,
  or an exception;
- never sleep through or automatically retry a rate limit;
- perform zero provider work on exact resume from a complete checkpoint;
- atomically write one schema-version-1 aggregate report with starting/ending
  coverage, slice and attempted counts, budget, checksums, halt, and failure;
- exclude symbols, currencies, paths, provider text, and exception messages.

Focused tests must cover multi-slice completion, partial last slice, budget
exhaustion and resume, rate-limit halt, zero progress, malformed checkpoint,
report-write failure, exact completed resume, and privacy.

## Exclusions

This audit does not change code or private evidence, run Yahoo, introduce
concurrency, sleeping, or scheduling, generate market-data batches, retrieve
candles, ingest data, analyze investments, or trade.

Next: implement the selected coordinator and CLI. A complete private run remains
blocked until that implementation passes focused and full regression tests.
