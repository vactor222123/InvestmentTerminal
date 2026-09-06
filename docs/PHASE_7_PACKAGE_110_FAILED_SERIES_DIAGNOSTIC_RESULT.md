# Phase 7 Package 110 — Failed-Series Diagnostic Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`8855a45216f7be35b47037473df27f691634706e`.

Only the explicitly returned redacted raw-series diagnostic report was
reviewed. The private manifest, checkpoint, cache, and instrument identity
remained private. SQLite was not opened by the diagnostic.

The diagnostic completed successfully and remained bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 19 of 601, request checksum
`bba88de6404ac7dae91b7a98aa32a6e0ac32f276bd1d332a7f8c0a449e4f4864`,
and the exact 2016-09-05 through 2026-09-05 request window.

The selected failed series returned two raw rows. One row is valid and one is
invalid. The only measured reason is `CLOSE_NON_FINITE` at
`2026-09-04T04:00:00+00:00`. Counts reconcile exactly and no identity or price
was exposed.

This proves the repeated `YahooCandleInvalidResponseError` is a local strict-
validation rejection of a non-finite close, not an undifferentiated transport
or provider failure. It does not yet prove that the invalid row is the trailing
row because the report intentionally does not expose the valid row timestamp.

Silently dropping arbitrary invalid rows would weaken historical integrity.
The next package must audit a narrowly bounded trailing-incomplete-candle
policy: preserve strict rejection for any invalid interior row and require
explicit evidence that an omitted row is the latest raw row. Do not retry batch
19 or execute batch 20/later batches before that audit.

Reviewed report SHA-256:
`df464ab69c1e1571c241dd1888f452a1c5819c991fe4946594de7747703f65a2`.

Verification:

- focused diagnostic/raw-client/Yahoo/manifest/architecture checks: 56 passed;
- complete local suite: 2,977 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
