# Phase 7 Package 109 — Manifest Failed-Series Diagnostic

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`5dc1a89b8ca0f287edd17e6d07a88355a7ce6d2e`.

This package implements the read-only boundary selected by Package 108. It
validates the complete private manifest and selected request checksum, requires
exact checkpoint outcome coverage with valid terminal statuses, and requires
exactly one failed outcome before any provider access.

The failed symbol is selected internally and requested once through the existing
raw Yahoo adapter over the exact manifest request start/end window. The existing
raw frame analyzer reports aggregate row validity and stable numeric/OHLC reason
counts without serializing identity or prices.

The schema-version-1 report contains manifest, batch, request, and window
bindings; aggregate selection evidence; raw/valid/invalid row counts; redacted
invalid timestamps and reason counts; timing; and privacy-safe failure evidence.
It excludes symbols, currencies, names, prices, paths, provider text, and
exception messages.

The service and CLI have no SQLite, repository, importer, or checkpoint-writer
dependency. The checkpoint is read only. This diagnostic does not retry or
ingest the failed series and does not authorize batch 20 or a manifest drain.

Run one controlled diagnostic for batch 19 next and return only its redacted
report. The manifest, checkpoint, and cache remain private.

Verification:

- focused service/CLI/raw-client/manifest/architecture checks: 35 passed;
- complete local suite: 2,977 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
