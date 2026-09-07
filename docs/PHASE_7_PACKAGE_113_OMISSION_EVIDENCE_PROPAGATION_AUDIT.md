# Phase 7 Package 113 — Omission Evidence Propagation Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`6d5fb0ba1fca0dd59c774b7c5c4bf7c929cf9e1e`.

## Consumer inventory

`YahooCandleProjection` now owns typed omission evidence, but the generic
`HistoricalDataClient` protocol still returns `list[Candle]`.
`HistoricalMarketService` calculates only downloaded, inserted, duplicate, and
stored counts. `HistoricalImportResult` has no omission fields.

`ResumableMarketBatchService` persists schema-version-1 outcomes containing
status, downloaded, inserted, duplicates, and failure type. Its schema-version-2
report aggregates only transfer counts. The manifest-bound schema-version-1
envelope forwards that coverage unchanged, while the schema-version-1 drain
aggregates the same three transfer totals.

Market refresh and other generic historical-import consumers read the existing
`HistoricalImportResult` fields. Enabling projection globally would therefore
change unrelated behavior and still fail to persist omission evidence.

## Rejected shortcuts

- Returning filtered candles through `get_candles` would silently lose omission
  evidence.
- Mutable `last_download_evidence` state on the Yahoo client would be unsafe for
  retries, concurrency, and deterministic tests.
- Optional unversioned checkpoint/report keys would make old, new, and partially
  migrated evidence ambiguous.
- Enabling the policy for generic refresh, weekly, or monthly requests would
  exceed the diagnosed daily manifest boundary.

## Selected versioned path

Implement a separate projected importer used only by manifest batch composition.
It obtains `YahooCandleProjection` with the explicit daily trailing policy,
persists only projected candles through the existing repository semantics, and
returns transfer counts plus immutable omission count/types. Generic historical
import and refresh remain strict.

Migrate the private resumable checkpoint contract to schema version 2. Schema-1
outcomes must be accepted and deterministically interpreted as zero omission;
the next attempted-item write must atomically emit a complete schema-2
checkpoint. Every schema-2 terminal outcome must explicitly contain
`omitted_trailing_count` and `omission_types`, including zero/empty values.
Invalid count/type combinations fail before resume decisions.

Emit resumable report schema version 3 with current-run and cumulative omission
totals plus sorted omission types. Version the manifest-bound envelope and drain
report when they expose that coverage. Drain aggregation must not discard
omission evidence, and mixed schema-1/schema-2 checkpoints must remain
deterministic during migration.

The implementation must prove:

- old zero-omission checkpoints resume without provider work and retain exact
  transfer accounting;
- the failed item can migrate and record one typed omission atomically;
- retry/persistence failure cannot produce a successful outcome without its
  omission evidence;
- exact repeat skips provider access and reproduces cumulative omission evidence;
- drain completion and aggregation recognize migrated successful outcomes;
- redacted reports contain no symbols, currencies, paths, prices, or provider
  messages;
- generic refresh and non-manifest historical ingestion remain strict;
- weekly/monthly trailing defects remain failures.

This is the smallest coherent vertical package. Batch 19 retry and batch 20+
remain blocked until it is implemented and all failure paths pass.

Verification:

- focused projection/import/batch/drain/refresh/architecture checks: 87 passed;
- complete local suite: 2,991 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
