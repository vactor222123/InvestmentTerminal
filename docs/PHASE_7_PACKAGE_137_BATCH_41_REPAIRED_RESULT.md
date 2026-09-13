# Phase 7 Package 137 - Batch-41 Repaired Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`2bfb7f7bbbb4b725119669f7e364b13fc9d21879`.

Only the explicitly returned redacted schema-version-2 repaired-series report
was reviewed. The private manifest, checkpoint, database, cache, symbols,
currencies, and candle values were not read or added to the repository.

## Measured result

The report is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 41 of 601, and request checksum
`8ab5bcb2053b95a2ce0c88987d7cc77daf07e14b681f1810f8ac3bcbe54c1163`.
It selected exactly the single failed checkpoint outcome and completed in
2.141236 seconds.

Explicit `YFINANCE_PRICE_REPAIR_V1` retrieval used yfinance 1.6.0. Yfinance
marked one of 2,514 rows as repaired, proving that the repair path performed a
provider-library transformation for this returned frame. Unchanged strict
projection nevertheless returned `REJECTED/RESPONSE_NUMERIC` with no projected
candle count. The transformation therefore did not make the complete series
acceptable for persistence.

The report SHA-256 is
`9b734e0a0581d8ff57f6f4895371d24a7dbedf7c33a72b8c05aeb334b5b208df`.

## Decision

Do not retry batch 41 through either normal or repaired retrieval. Do not
persist the rejected repaired frame, silently remove an interior row, or weaken
strict numeric validation. Batch 42 and the broader drain remain blocked while
the current coordinator treats one failed series as a batch-level stop.

Audit the smallest durable terminal-series isolation boundary next. The audit
must determine how an irreparable series remains explicit and checksum-bound
without blocking unrelated later batches, while preserving exact-resume,
coverage accounting, failure categories, and fail-closed persistence. It must
inspect existing checkpoint, one-batch report, and drain consumers before
selecting a versioned contract. It must not contact Yahoo, mutate private
runtime evidence, infer replacement values, or implement the change.

## Verification scope

Focused repaired-series, failed-series, Yahoo projection, manifest execution,
drain, and architecture tests plus the complete suite and whitespace gate
remain mandatory for this operational record.

Verification:

- focused repaired/failed diagnostics, manifest execution/drain, and
  architecture tests: 59 passed;
- complete suite: 3,036 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
