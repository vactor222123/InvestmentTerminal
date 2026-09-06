# Phase 7 Package 108 — Failed Batch Series Diagnostic Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`5f611273db0646cf234061532f48298a88c3117b`.

## Factual findings

The existing `YahooRawCandleDiagnosticClient` already requests one unconverted
daily frame with the same yfinance history options used by the production Yahoo
candle client: explicit start/end, `1d`, no auto-adjustment, no actions, no
repair, and raised provider errors.

The existing `_analyze_frame` boundary already measures raw/valid/invalid row
counts, stable numeric and OHLC reason counts, and redacted timestamps without
serializing symbols or prices. It is therefore reusable.

`SingleSeriesCandleDiagnosticService` itself is not reusable for batch 19. It
requires an eligibility request and schema-version-3 eligibility checkpoint,
selects only `FINAL_FAILED/RESPONSE_NUMERIC`, and derives the fixed eligibility
window. Batch 19 instead owns a schema-version-1 request-checksum-bound market
checkpoint and the manifest's ten-year request window.

The resumable batch checkpoint stores `YahooCandleInvalidResponseError` only as
a class name. Its report therefore cannot distinguish response numeric, OHLC,
timestamp, shape, or candle-set validation categories. The repeated retry adds
no causal evidence beyond the unchanged class.

## Selected boundary

Implement a separate read-only manifest-bound failed-series diagnostic. It
must validate the manifest checksum, selected batch/request checksum, exact
checkpoint outcome coverage, and exactly one failed outcome before provider
access. It may select the private symbol/currency internally, request only that
raw series over the manifest request's exact window, and reuse the existing raw
frame analyzer.

The report must contain only manifest/request bindings, aggregate selection and
row/reason counts, timing, and privacy-safe failure types. It must not expose
the symbol, currency, prices, paths, provider text, or exception messages. It
must not open SQLite, write the checkpoint, ingest candles, retry the batch, or
authorize batch 20.

The separate SQLite integrity wrapper failure remains unclassified operational
evidence. This diagnostic must not couple database inspection to raw provider
diagnosis.

Verification:

- focused raw-client/analyzer/manifest/architecture checks: 57 passed;
- complete local suite: 2,969 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
