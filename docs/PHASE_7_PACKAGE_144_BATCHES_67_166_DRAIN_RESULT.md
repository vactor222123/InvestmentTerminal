# Phase 7 Package 144 — Batches 67–166 Drain Result

## Classification

`OPERATIONAL`

## Verified Baseline

```text
develop @ 925932f0b9849bbf3b8508747590bb0992a19e2e
```

## Reviewed Evidence

The user returned only the redacted schema-version-3 `MANIFEST_BATCH_DRAIN`
report and separately reported SQLite `integrity_check=ok`. Private manifest,
checkpoints, database, cache, candle values, currencies, and instrument
identities were not reviewed.

Report SHA-256:

```text
1ad00984f7da0633f43b5aaa5679945bd39b029fe4b53b353b3a3cfea7fe0b62
```

The report is bound to the established manifest:

```text
manifest_checksum = 8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a
batch_count = 601
max_batches = 100
```

## Result

The bounded drain returned `HALTED` at the first non-success batch:

```text
starting completed_batch_count = 66
starting remaining_batch_count = 535
current attempted_batch_count = 39
current attempted_item_count = 780
current downloaded_total = 1050735
current inserted_total = 1050735
current duplicate_total = 0
current omitted_trailing_total = 0
ending completed_batch_count = 104
ending remaining_batch_count = 497
stop_batch_index = 105
failure_types = [YahooCandleInvalidResponseError]
```

The run therefore completed exactly batches 67–104 and did not begin batch 106.
No duplicate, trailing omission, or new final exclusion was reported. The
existing batch-41 evidence remained visible in starting and ending coverage as
one final `RESPONSE_NUMERIC` exclusion. SQLite integrity was checked separately
and reported `ok`.

## Limits

This result establishes aggregate progress and the failure boundary only. The
redacted drain report does not identify which private series in batch 105
failed or why its Yahoo response was invalid. It does not establish coverage
for batch 105 or later batches and does not authorize a retry, another drain,
scheduling, analysis, or trading. SQLite integrity is operator-reported
evidence separate from the redacted JSON report.

No application, persistence, architecture, data-model, or JSON-contract change
is required.

## Verification

- focused manifest drain/resume and architecture tests: 45 passed;
- complete suite: 3,050 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next Operational Gate

Run the existing read-only manifest batch checkpoint diagnostic for batch 105.
Return only its redacted diagnostic report. Do not retry batch 105 or start
batch 106 before reviewing that evidence.
