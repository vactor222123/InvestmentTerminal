# Phase 7 Package 143 — Manifest Drain Budget 100

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ de8416fe7942758728c37b55a2e70c3ed6307e6e
```

## Audit

The manifest drain is sequential and already persists a private checkpoint
after every attempted item. It derives the first unfinished batch from exact
request-bound checkpoints and stops before the next batch on the first
non-success result. Increasing its run budget therefore changes neither
concurrency nor provider request rate and does not weaken restart, ordering,
failure-isolation, or persistence semantics.

The previous maximum of 25 batches was an implementation guard, not a provider
or SQLite limit. Package 142 operationally completed that full budget: 500
items and 655,813 inserted candles in 234.066194 seconds with no failures,
duplicates, or omissions and with SQLite integrity `ok`.

## Change

`ManifestBatchDrainPlan` now accepts an explicit `max_batches` value from 1
through 100. Zero, booleans, values above 100, non-integers, invalid manifests,
out-of-order checkpoints, and non-success batch outcomes remain fail-closed.

The existing report schema is unchanged. It already records the caller's exact
budget and all starting, current-run, ending, stop, failure, omission, and final
exclusion evidence. Per-request checkpoints, 20-item batch limits, sequential
execution, and stop-on-first-non-success behavior are unchanged.

## Verification

- focused manifest drain/CLI/architecture tests: 26 passed;
- complete suite: 3,050 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next Operational Gate

Run one bounded manifest drain with `max_batches=100`. Exact checkpoint ordering
must select batch 67 first and permit at most batches 67–166. Stop on the first
non-success result, return only the redacted drain report, and verify SQLite
integrity separately. Do not start another drain until that result is reviewed.
