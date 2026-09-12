# Phase 7 Package 129 - Repaired-Series Integration Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`d27fb2b7178e0871ce3a6b083412dcbc0d60245b`.

## Finding

The repaired-series qualification is intentionally read-only and keeps its
provider transformation evidence inside its own report. The production
manifest path still requests Yahoo history with `repair=False`, projects the
frame through `ProjectedHistoricalMarketService`, and persists ordinary
`Candle` values. Its checkpoint and report schemas carry outcome counts and
typed trailing-omission evidence, but no retrieval-mode or repaired-row
provenance. The `Candle` aggregate, SQLite `candles` table, repository API, and
uniqueness key likewise contain no acquisition or transformation provenance.

Therefore a direct `repair=True` integration would lose the fact that a
heuristic provider transformation was requested before the data reached the
durable boundary. Adding a database migration and end-to-end repair provenance
contract would be a broad change, and Package 128 does not justify it: the
qualified frame contained one row and yfinance marked zero rows as repaired.
That result does not show that repair changed any candle.

The existing schema-version-2 manifest failed-series diagnostic fetches the
exact normal `repair=False` frame and applies the shared trailing-incomplete
assessment, but that assessment answers only whether one invalid final row may
be omitted. A fully valid frame consequently produces
`REJECTED/NO_INVALID_ROW`; it does not record whether unchanged strict
projection accepts the complete frame or how many candles it projects.

## Selected boundary

Do not integrate or persist repaired retrieval. First extend the existing
read-only manifest failed-series diagnostic to schema version 3. On the same
already-fetched `repair=False` frame, it must additionally execute unchanged
strict Yahoo projection and report one redacted `strict_projection` object:

- `status`: `QUALIFIED`, `EMPTY`, or `REJECTED`;
- `projected_candle_count`: a non-negative integer when projection completes,
  otherwise null;
- `failure_category`: the existing stable Yahoo failure category only when
  projection is rejected, otherwise null.

Historical schema-version-1 and schema-version-2 reports remain immutable.
The new evidence must not add a provider request or expose symbol, currency,
timestamps, prices, volumes, paths, exception messages, or raw provider text.
The service remains free of database, repository, importer, checkpoint-writer,
retry-loop, and drain dependencies.

## Decision gate

After implementation, run exactly one controlled diagnostic for the existing
batch-19 failed outcome and return only the redacted schema-version-3 report.
If unchanged strict projection is `QUALIFIED`, review whether the normal
batch-19 retry is warranted without repair. If it is `REJECTED`, keep
persistence blocked and audit an explicit end-to-end repair provenance model.
Neither result alone authorizes batch 20 or the broader drain.

## Verification scope

This audit performs no Yahoo request and does not read or mutate the private
manifest, checkpoint, cache, database, or runtime reports. Focused tests cover
the current manifest diagnostic, repaired qualification, production projection,
resumable checkpoint/report, persistence, and architecture boundaries. The
complete suite and whitespace gate remain mandatory.

Verification:

- focused diagnostic, repair, projection, checkpoint, persistence, and
  architecture tests: 67 passed;
- complete suite: 3,033 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
