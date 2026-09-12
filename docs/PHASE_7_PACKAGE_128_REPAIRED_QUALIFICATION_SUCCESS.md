# Phase 7 Package 128 - Repaired Qualification Success

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`8417fd7f26e8ca2203117d54cf944f18eaf0c749`.

Only the explicitly returned redacted schema-version-2 report was reviewed.
The private manifest, checkpoint, cache, database, symbol, currency, and candle
values were not read or added to the repository.

## Measured result

The report is structurally valid and bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 19 of 601, request checksum
`bba88de6404ac7dae91b7a98aa32a6e0ac32f276bd1d332a7f8c0a449e4f4864`,
and the established ten-year half-open window from 2016-09-05 through
2026-09-05.

Status is `QUALIFIED`. The explicit yfinance 1.6.0 repair path returned one raw
row, and unchanged strict Yahoo projection accepted one candle with no failure
category. Repair was requested through `YFINANCE_PRICE_REPAIR_V1`, but the
returned evidence marks zero repaired rows and `any_repaired_rows=false`.
Execution took 1.482599 seconds. The report SHA-256 is
`0bd915c8ef89a737f513fbb16566f26bc92117bb1be61eb00d271bb09b07829f`.

## Interpretation and boundary

This measurement proves only that the one frame returned by the explicit
`repair=True` request was non-empty and structurally acceptable to the existing
strict projection. It does not prove that yfinance repaired a row, explain why
the earlier two-row response became a one-row response, establish ten-year
coverage completeness, or qualify the unchanged production `repair=False`
path. No checkpoint or SQLite mutation was performed.

Package 120's future-integration guard therefore remains active. The next
package must audit how repair-mode provenance, zero-versus-nonzero repaired-row
evidence, checkpoint/report semantics, and stored-candle provenance would be
carried before any persistence is authorized. It must also decide whether an
unchanged read-only production-path measurement is required before choosing an
integration. Do not retry batch 19 ingestion, execute batch 20, or resume the
broader drain before that audit.

## Verification

The report SHA-256 was independently verified before documentation. Focused
repaired-client, qualification, dependency-contract, and architecture checks
passed with `38 passed`. The complete suite passed with `3033 passed, 4
skipped, 1 warning`; the warning is the existing Starlette `httpx` deprecation
warning. `git diff --check` is clean.
