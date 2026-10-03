# Phase 7 — full stored-close indicator result and research-export audit

Classification: `AUDIT`. A fresh clean GitHub `develop` clone matched
`f7177ba009e45a22848871ac275ff4776bb453bb`. The only runtime document
reviewed was the explicitly returned redacted
`LATEST_RAW_INDICATOR_PROJECTION_REPORT` at
`C:\runtime\reports\latest_raw_indicator_projection_20260929_full.json`;
its verified SHA-256 is
`1cc1b7b09ff1ddf84699a9e137af44e07044f373680af6a01eafbbe6c976d184`.
The user separately reported `SQLite integrity: ok`. The private value
document, manifest, checkpoints, and database were not inspected or changed.

## Reconciled measurement

The schema-version-1 report is `COMPLETE`, with `failure=null`, exactly
11,892 selected and processed series, and `max_items=11892`. It is bound to
manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
selection checksum
`75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`,
exclusive end `2026-09-29T00:00:00+00:00`, and price basis
`STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`. These bindings match the prior
one-item handoff. The availability bins reconcile: 0 `NO_CANDLES` + 295
`UNDER_50` + 1,358 `50_TO_199` + 10,239 `BOTH_AVAILABLE` = 11,892.
SMA50 availability is 1,358 + 10,239 = 11,597; SMA200 availability is
10,239. The seven-calendar-day latest-candle proxy holds for 11,787;
105 do not meet it. The 1,653 series without SMA200 are not automatically
data defects: listing/fund inception, provider coverage, and other causes
are not determined by this report.

The report does not give intersections between SMA availability, recency,
weekly outcome, observed age, or calendar gaps. In particular, it cannot
establish how many SMA200 series are also recent, much less session-complete.
The latest 200 stored closes are a sample, not 200 verified trading sessions.
The prior explicit-window stored-coverage report independently recorded
10,239 series with at least 200 rows; matching totals are a consistency
check, not a substitute for per-series quality or adjusted-price evidence.

## Product and code boundary

`latest_raw_indicator_projection` already writes a private, all-series
value document and a separate redacted aggregate; its code reads a complete
manifest-bound weekly checkpoint and SQLite snapshot, applies no Terminal-side
corporate-action adjustment, and makes no provider request or investment
interpretation. The report cannot itself support an instrument-level ChatGPT
analysis because it intentionally excludes symbols, timestamps, prices, and
SMA values. Sending the full private projection would bypass the established
private/runtime boundary and provide no bounded question-specific context.
The existing weekly CLI updates candles in separate bounded slices; neither
its status nor this full projection constitutes an unattended weekly pipeline.

## Selected next implementation

Implement one **read-only, bounded, private instrument research export** as a
separate operations/CLI boundary. An explicit query symbol is a request for
analysis, not manual market-data entry. Resolve it against the validated
manifest selection; bind the export to the complete private projection's
manifest/selection/end/price-basis fields and a checksum of the exact source
projection bytes. Export only that selected instrument's already stored
daily candles within an explicit bounded window, its current raw-close
SMA50/SMA200 evidence, weekly outcome, sample count, and objective recency/
coverage limitations. The private export stays under `C:\runtime\data`;
emit a separate redacted report suitable for operational review. Neither
file should be sent to ChatGPT automatically. Preserve the existing candle,
weekly checkpoint, and projection JSON schemas. Reuse the existing read-only
SQLite and atomic-write conventions; refuse a missing/mismatched symbol,
wrong checksum, stale or mismatched projection binding, invalid stored row,
or existing output path. Focused and failure-path tests should cover those
guards, deterministic ordering, redaction, and no database writes.

This is a narrow route from the collected database to a reviewable factual
instrument artifact, not a recommendation engine. A later explicit user-
approved sharing/connector boundary can make such artifacts available to
ChatGPT. Corporate-action policy, exchange-session completeness, portfolio
performance, multi-symbol bulk export, and unattended weekly scheduling
remain separate gates. No provider retry, candle rewrite, or runtime action
is authorized by this audit.
