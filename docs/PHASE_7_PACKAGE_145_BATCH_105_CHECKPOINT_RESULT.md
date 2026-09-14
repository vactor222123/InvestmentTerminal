# Phase 7 Package 145 — Batch 105 Checkpoint Result

## Classification

`OPERATIONAL`

## Verified Baseline

```text
develop @ bb9aa70da3ca86fa54a7ed601479c076c30e70cd
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-2 checkpoint diagnostic
was reviewed. The private manifest, checkpoint, database, cache, symbol,
currency, candle values, and provider response remained private.

Report SHA-256:

```text
b2aacff282f7eb75227c5cc2722388a29c7cb90dc56598327ad36252e1fbf8d2
```

The successful report is bound to:

```text
manifest_checksum = 8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a
batch_index = 105
batch_count = 601
request_checksum = adad810e4fe1236ed028d44a85c43477ce1e28d6195ef7eedd6ab9514b9bb588
```

## Result

All 20 requested outcomes reconcile exactly:

```text
success_count = 19
empty_count = 0
retryable_failure_count = 1
final_failure_count = 0
failure_types = [YahooCandleInvalidResponseError]
final_failure_categories = []
```

The batch-105 drain halt is therefore isolated to one retryable private series;
it is not a complete-batch failure. The read-only diagnostic did not call
Yahoo, open SQLite, or modify the manifest or checkpoint.

## Limits

The report does not identify the failed series or explain the invalid response.
It does not authorize retry, batch 106, another drain, scheduling, analysis, or
trading. No application, persistence, architecture, data-model, or JSON-
contract change is required.

## Verification

- focused checkpoint/raw-diagnostic/manifest/architecture tests: 48 passed;
- complete suite: 3,050 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next Operational Gate

Run the existing manifest-bound failed-series raw candle diagnostic for batch
105. It must internally select exactly the one failed outcome and use the
manifest's ten-year window. Return only the redacted report. Do not retry batch
105 or start batch 106 before review.
