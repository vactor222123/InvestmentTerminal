# Phase 7 Package 103 — Five-Batch Drain Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`d1effe105f7f98b644d565344328d722cb5d0e08`.

Only the explicitly returned redacted aggregate report was reviewed. The
private manifest, per-batch checkpoints, Yahoo cache, and market SQLite remained
private.

The first bounded drain returned `BUDGET_EXHAUSTED` after its exact five-batch
budget in 19.625001 seconds. Starting coverage correctly identified one complete
batch and 600 remaining. The run attempted five batches and 100 items, then
ended with six complete batches and 595 remaining. No stopping batch or failure
type was reported.

The run downloaded 143,049 candles, inserted 140,542, and reported 2,507
duplicates. The transfer accounting reconciles exactly: downloaded minus
inserted equals duplicates. Existing SQLite evidence can therefore explain the
duplicates without implying a current failure, but the redacted report does not
identify which private item overlapped.

The manifest checksum remains
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`.
The reviewed report SHA-256 is
`d57325c7198d4ce0e9a5186eaab71f9c62c86c4e31abba4fc73584af569efef3`.

This establishes successful bounded coordination through batch 6. It does not
measure calendar completeness, freshness, or later manifest requests. The next
controlled operation may use the already implemented maximum `max_batches=25`;
it may attempt only batches 7–31 and must stop on the first non-success result.
No complete-manifest drain or scheduling is authorized.
