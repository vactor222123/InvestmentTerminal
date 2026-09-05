# Phase 7 Package 105 — Batch Checkpoint Diagnostic

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`d543fa9f1fc179064285cdaebeec3c19b29bb738`.

Package 104 proved that the bounded drain halted at batch 19 but its drain-level
report did not expose the stopped checkpoint's aggregate outcome distribution.
Retrying would alter that evidence before measurement.

This package adds a read-only diagnostic for exactly one caller-selected,
manifest-bound checkpoint. It validates the manifest checksum, contiguous batch
selection, request checksum, exact requested-symbol coverage, terminal status
vocabulary, and failure-type shape. The emitted schema-version-1 report contains
only requested, success, empty, and failure counts plus sorted failure types and
non-private binding metadata.

The diagnostic has no Yahoo client, SQLite database, importer, or checkpoint
writer. Its CLI reads the private manifest/checkpoint and atomically writes a
separate redacted report. Success means the diagnostic completed; checkpoint
failures remain visible in `coverage.failure_count` and do not turn diagnostic
execution itself into failure.

Next, run the diagnostic for batch 19 and return only its redacted report. Do
not retry batch 19 or execute a later batch until the aggregate result is
reviewed.

Verification:

- focused diagnostic, CLI, binding, and architecture tests: 29 passed;
- complete local suite: 2,969 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
