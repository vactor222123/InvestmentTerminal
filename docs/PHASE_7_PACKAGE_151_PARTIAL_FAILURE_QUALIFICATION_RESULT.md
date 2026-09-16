# Phase 7 Package 151 — Partial Failure Qualification Result

## Classification

`OPERATIONAL`

## Verified Baseline

```text
develop @ 1a38534de1ccf6c2c5069f1f280db1a9cd0ce9a1
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-1
`MANIFEST_PARTIAL_FAILURE_QUALIFICATION` report was reviewed. The private
manifest, batch-106 checkpoint, Yahoo cache, symbols, currencies, prices, raw
provider response, and SQLite database were not reviewed or modified.

Report SHA-256:

```text
6a88fef1629287a395faecb04ba6d1ba72587d582573a99b4d211684aad9ce05
```

The report binds exactly to the established manifest and partial request:

```text
manifest_checksum = 8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a
batch_index = 106
batch_count = 601
request_checksum = e75eb6f083b162d8f1998a37bef9814265415adf15335008f6b4a64b97949ab9
requested_count = 20
checkpoint_outcome_count = 7
missing_count = 13
failed_candidate_count = 1
selected_count = 1
checkpoint_failure_types = [APIError]
```

## Result

The one read-only production-path request completed in 0.48513 seconds and
returned `FAILED`. The existing causal projection classified the current
failure as:

```text
category = NO_PRICE_DATA
exception_type_chain =
  investment_terminal.utils.exceptions.APIError
  -> yfinance.exceptions.YFPricesMissingError
```

This establishes that the exact selected series currently reproduces an
explicit Yahoo no-price result. It does not reconstruct or prove the cause of
the original batch-106 failure because checkpoint schema 3 persisted only the
outer `APIError` class. Coverage therefore correctly remains null.

The qualification opened no SQLite database, ingested no candles, and wrote no
checkpoint. Batch 106 remains partial with 13 items not attempted, and batch
107 remains blocked.

## Boundary Audit

The existing terminal-series isolation contract cannot be reused unchanged.
It requires exact complete-request checkpoint coverage, matching normal and
repaired strict-rejection reports, and permits only `RESPONSE_NUMERIC` or
`RESPONSE_OHLC`. It correctly rejects `NO_PRICE_DATA` and cannot transition
this partial generic `APIError` evidence.

Do not manually rewrite the checkpoint, treat the current measurement as the
lost original cause, retry the same ingestion blindly, or weaken the existing
terminal-isolation policy. A future-safe remediation must bind immutable report
bytes/checksum to this exact manifest request and must preserve typed causal
evidence when later provider failures are checkpointed instead of erasing it.

## Next Gate

Perform a focused audit of an evidence-bound partial-checkpoint terminal
transition for the reproduced `NO_PRICE_DATA` result and of versioned causal
failure persistence for future collection attempts. Select the smallest schema
change that preserves existing checkpoints and diagnostics. Do not contact
Yahoo, mutate runtime evidence, rerun the sweep, retry batch 106, or permit
batch 107 during that audit.
