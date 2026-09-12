# Phase 7 Package 130 - Normal-Path Strict-Projection Evidence

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`41d724e740e098f63ca8f1084aca4bf0c4d37896`.

## Result

The manifest failed-series diagnostic now projects its already-fetched raw
Yahoo frame through `YahooFinanceClient.project_history_frame_strict`. It does
not make a second provider request. The report advances to schema version 3 and
adds `coverage.strict_projection` with only:

- `status`: `QUALIFIED`, `EMPTY`, or `REJECTED`;
- `projected_candle_count`: the completed strict count or null on rejection;
- `failure_category`: null after completed projection or the existing stable
  Yahoo category after rejection.

`QUALIFIED` means strict production projection accepted one or more candles.
`EMPTY` means it completed with zero candles without inventing an error.
`REJECTED` means the existing strict policy raised a typed Yahoo validation
error. The diagnostic's outer status remains `SUCCESS` when it successfully
measures any of these three outcomes.

## Compatibility and safety

Historical schema-version-1 and schema-version-2 report files remain immutable.
The schema-version-3 report preserves all prior manifest, request, selection,
raw coverage, trailing-assessment, timing, failure, and limitation fields. Its
CLI failure envelope also uses schema version 3.

Focused tests cover a valid frame, an empty frame, numeric rejection, OHLC
rejection, redaction, exact checkpoint validation before provider access, one
raw request, and unchanged checkpoint bytes. The service still has no SQLite,
repository, importer, checkpoint-writer, retry-loop, or drain dependency. No
runtime request or private input was used in this implementation package.

## Next action

Run exactly one controlled schema-version-3 diagnostic for the existing failed
batch-19 outcome and return only the redacted report. The private manifest,
checkpoint, cache, database, symbols, currencies, and candle values must not be
returned. Do not retry ingestion, execute batch 20, or resume the broader drain
before the report is reviewed.

## Verification

- focused raw-client, diagnostic, repair, projection, checkpoint, and
  architecture tests: 109 passed;
- complete suite: 3,036 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
