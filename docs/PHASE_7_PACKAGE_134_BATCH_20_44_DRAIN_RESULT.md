# Phase 7 Package 134 - Batch-20-to-44 Drain Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`455d52867d20aa0286109fb49bc14326d8645f72`.

Only the explicitly returned redacted drain report and privacy-safe SQLite
integrity result were reviewed. The private manifest, checkpoints, database,
cache, symbols, currencies, and candle values were not read or added to the
repository.

## Measured result

The schema-version-2 drain report is valid and bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and the explicit 25-batch budget. It started with 19 complete batches and 582
remaining.

The coordinator returned `HALTED` after 197.345387 seconds. It attempted 22
batches and 440 items. Batches 20 through 40 completed, raising contiguous
coverage to 40 batches with 561 remaining. Batch 41 is the explicit stop index
and reports `YahooCandleInvalidResponseError`; batch 42 was not attempted.

The run downloaded and inserted 602,174 candles with zero duplicates, zero
trailing omissions, and no omission types. Transfer accounting reconciles
exactly. The report SHA-256 is
`75a19942fc55a5bc5de092c647a4576a9d8f647e05ef0e1745b1efa059d6d3db`.
The separately returned read-only SQLite result is `integrity_check = ok`.

## Decision

The coordinator respected the restart, budget, and stop-on-first-non-success
contracts. This report proves only that batch 41 contains at least one failed
outcome; it does not expose the private checkpoint's aggregate success, empty,
and failure counts. Do not retry batch 41 or resume the drain yet.

Run the existing read-only manifest-bound checkpoint diagnostic exactly once
for batch 41. Return only its redacted report. It must validate the manifest,
request, exact outcome coverage, terminal statuses, and failure types without
opening SQLite, contacting Yahoo, or mutating the checkpoint. Batch 42 and all
later execution remain blocked pending review.

## Verification scope

Focused drain, checkpoint-diagnostic, manifest, resumable execution, and
architecture tests plus the complete suite and whitespace gate remain
mandatory for this operational record.

Verification:

- focused drain, checkpoint-diagnostic, manifest, resumable, and architecture
  tests: 48 passed;
- complete suite: 3,036 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
