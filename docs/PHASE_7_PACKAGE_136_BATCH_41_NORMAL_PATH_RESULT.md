# Phase 7 Package 136 - Batch-41 Normal-Path Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`7d5a24f7a7477071deed362535e9e1fe818cf6f7`.

Only the explicitly returned redacted schema-version-3 diagnostic report was
reviewed. The private manifest, checkpoint, database, cache, symbols,
currencies, and candle values were not read or added to the repository.

## Measured result

The report is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 41 of 601, and request checksum
`8ab5bcb2053b95a2ce0c88987d7cc77daf07e14b681f1810f8ac3bcbe54c1163`.
It completed with status `SUCCESS` after selecting the single failed
checkpoint outcome.

Normal `repair=False` retrieval returned 2,514 rows: 2,513 valid rows and one
invalid row at `2016-12-28T05:00:00+00:00`. The row has both
`OPEN_NON_POSITIVE` and `LOW_NON_POSITIVE`. It is not the final row, so the
daily trailing-row omission policy correctly rejected it with
`INVALID_ROW_NOT_FINAL`. Unchanged strict projection also returned `REJECTED`
with stable failure category `RESPONSE_NUMERIC` and no projected candle count.

The report SHA-256 is
`149b0732f613503e62ea495c0fd674d6010543408727d38677a91addb00901f5`.

## Decision

Do not retry batch 41 through the normal path: the current response reproduces
the causal defect and would deterministically fail again. Do not broaden the
trailing-row policy or silently discard the interior row. Batch 42 and the
broader drain remain blocked.

Run the existing separate manifest-bound repaired-series qualification exactly
once for batch 41. It may make one explicit `repair=True` request and apply
unchanged strict projection, but it remains read-only and must not mutate the
checkpoint or database. Review only its redacted schema-version-2 report to
measure whether yfinance marks or changes the invalid interior row. A
qualification result does not authorize persistence: repaired-data provenance
still requires a separate explicit integration decision.

## Verification scope

Focused failed-series, repaired-series, Yahoo projection, manifest, and
architecture tests plus the complete suite and whitespace gate remain
mandatory for this operational record.

Verification:

- first focused attempt: 91 passed and 13 setup errors because the nested
  repository-local basetemp parent was removed by pytest; no test failed;
- corrected focused diagnostic, repair qualification, Yahoo projection,
  manifest, and architecture run: 104 passed;
- complete suite: 3,036 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
