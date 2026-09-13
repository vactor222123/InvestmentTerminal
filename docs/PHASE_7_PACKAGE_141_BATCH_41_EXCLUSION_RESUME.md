# Phase 7 Package 141 — Batch-41 Exclusion Resume

## Classification

`OPERATIONAL`

## Verified Baseline

```text
develop @ 5f7f28e1b6f5a0ce307bdeaec4bc3cff28e24967
```

## Reviewed Evidence

The user returned only the redacted schema-version-3
`MANIFEST_BOUND_MARKET_BATCH` report and separately reported SQLite
`integrity_check=ok`. Private manifest, checkpoint, database, cache, candle
values, currencies, and instrument identities were not reviewed.

Report SHA-256:

```text
d4ff1b4b19912ff9d7df0fbaaa95d6ac6f3743b24ebe70949bd1ad2b71a41ad3
```

The report remains bound to the established immutable inputs:

```text
manifest_checksum = 8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a
batch_index = 41
batch_count = 601
request_checksum = 8ab5bcb2053b95a2ce0c88987d7cc77daf07e14b681f1810f8ac3bcbe54c1163
```

## Result

The exact resume returned `SUCCESS_WITH_EXCLUSIONS`:

```text
current attempted_count = 0
current skipped_count = 20
current downloaded_total = 0
current inserted_total = 0
current duplicate_total = 0
current omitted_trailing_total = 0

cumulative requested_count = 20
cumulative success_count = 19
cumulative empty_count = 0
cumulative retryable_failure_count = 0
cumulative final_failure_count = 1
final_failure_categories = RESPONSE_NUMERIC
```

The zero-attempt result demonstrates that the resumable boundary skipped all
20 terminal outcomes, including the evidence-bound final exclusion. Under the
implemented service contract, no importer or Yahoo request is made for skipped
outcomes. The operational command also verified that the checkpoint checksum
did not change. SQLite integrity was checked separately and reported `ok`.

Batch 41 therefore no longer blocks ordered manifest progress. Its one final
exclusion remains explicit and is not reclassified as success, empty data, or
a retryable failure.

## Limits

This result proves exact-resume behavior only for batch 41 and its current
checkpoint. It does not establish coverage or success for batch 42 or any
later batch, and it does not authorize an unbounded drain, scheduling,
analysis, or trading. SQLite integrity is operator-reported evidence separate
from the redacted JSON report.

No application, persistence, or JSON-contract change is required. Architecture
and data-model documents therefore remain unchanged.

## Verification

- focused manifest resume/drain and architecture tests: 45 passed;
- complete suite: 3,049 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next Operational Gate

Run one existing bounded manifest drain with `max_batches=25`. Exact checkpoint
ordering must select batch 42 as the first attempted batch and permit at most
batches 42–66. Stop on the first non-success result, return only the redacted
drain report, and verify SQLite integrity separately. Do not start another
drain until that result is reviewed.
