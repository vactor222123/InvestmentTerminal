# Phase 7 Package 139 — Evidence-Bound Terminal-Series Isolation

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ 3c317dd2746c8214aaf2e5df84acbd1ce2945fa0
```

## Result

The Package 138 contract is implemented without Yahoo access, SQLite access,
or private runtime mutation. A new manifest-bound operation validates the
private manifest/checkpoint and the caller-supplied SHA-256 values of both the
normal diagnostic and repaired qualification before changing one retryable
outcome from `FAILED` to `FINAL_FAILED`.

Policy `NORMAL_AND_REPAIRED_STRICT_REJECTION_V1` permits the transition only
when both exact reports bind to the same manifest, batch, request, and window,
select the same single checkpoint failure, and reject strict projection with
the same `RESPONSE_NUMERIC` or `RESPONSE_OHLC` category. Other failures,
mismatches, malformed JSON, and conflicting evidence fail closed.

## Versioned Contracts

- checkpoint schema 3 stores the original failure type, stable category,
  policy identity, and both evidence checksums on `FINAL_FAILED`;
- the isolation report uses schema 1 and contains only bindings, aggregate
  transition counts, policy/category, and evidence checksums;
- resumable batch report schema 4 and manifest envelope schema 3 expose
  retryable and final failures separately and use
  `SUCCESS_WITH_EXCLUSIONS` when only final exclusions remain;
- drain report schema 3 treats `FINAL_FAILED` as terminal, advances to later
  batches, and reports starting/current/ending exclusion evidence;
- checkpoint diagnostic schema 2 reports retryable and final failures
  separately;
- legacy checkpoint schemas 1 and 2 remain readable, while failed-series
  diagnostics still select only `FAILED` and cannot reopen a final outcome.

The exact same evidence is idempotent. Different evidence for an existing
final outcome is rejected before checkpoint write. The CLI writes the private
checkpoint before claiming success in the separate redacted report.

## Scope

This package does not retrieve or persist candles, contact Yahoo, alter the
`Candle` model or SQLite schema, execute batch 41 or 42, or authorize the wider
drain. `FINAL_FAILED` applies only to the fixed checksum-bound manifest request;
it does not declare the instrument permanently invalid for later manifests or
windows.

## Verification

- focused terminal-isolation, resumable/manifest/drain/diagnostic, CLI, and
  architecture tests: 81 passed;
- complete suite: 3,049 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next Operational Gate

Run exactly one controlled terminal-series isolation for the already measured
batch-41 normal and repaired evidence. Return only the redacted schema-1
isolation report and verify SQLite integrity separately. Do not run batch 42 or
the broader drain until that transition is reviewed.
