# Phase 7 Package 120 - Repaired Retrieval Qualification Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`b45768e24c9678b1b783b6a1de7d6be6cc6350eb`.

## Scope and evidence

This audit inspects only the repository, its locked dependency contract, and
the installed yfinance `1.6.0` implementation. It does not contact Yahoo,
inspect private identities, open SQLite, change a checkpoint, retry ingestion,
or authorize batch 20.

The production `YahooFinanceClient` and raw diagnostic adapter both call
`Ticker.history(..., repair=False)`. Package 119 proved that the one failed
batch-19 series has a final non-finite close accompanied by internally
inconsistent finite OHLC values. The shared omission policy therefore correctly
returns `REJECTED/TRAILING_PARTIAL_OHLC_INCONSISTENT`.

yfinance `1.6.0` documents `repair=True` as a heuristic repair facility for
price errors including missing values, unit errors, and dividend adjustments.
Its implementation can fetch finer-grained history recursively, recalculate
high/low values, add `Repaired?`, and perform currency-related corrections.
It is consequently a materially different provider-library transformation,
not validation of the original Yahoo frame and not an independent source.

## Decision

The smallest safe next implementation is a separate read-only, one-series
qualification. It must not add a `repair` switch to the production client or
silently change the existing raw diagnostic.

The qualification must:

1. validate the private manifest, batch-19 request, and checkpoint bindings
   before provider access, and select exactly the single failed outcome;
2. make exactly one explicit daily `Ticker.history` request for the manifest's
   existing half-open window with `auto_adjust=False`, `actions=False`, and
   `repair=True`;
3. strictly project the returned frame through the existing production candle
   validator with trailing omission disabled;
4. emit a separate atomic schema-version-1 redacted report containing the
   manifest/request bindings, requested window, yfinance version, explicit
   repair method identity, aggregate raw/projected counts, qualification status,
   stable failure category, and whether any returned row was marked repaired;
5. exclude symbol, currency, candle values, paths, provider text, exception
   messages, and row-level identity from the report;
6. remain read-only: no SQLite, importer, checkpoint writer, retry loop, fallback
   chain, or later-batch execution.

The result vocabulary is closed: `QUALIFIED`, `REJECTED`, or `FAILED`.
`QUALIFIED` requires a non-empty frame whose complete strict projection passes;
it proves only that this explicitly transformed retrieval is structurally
acceptable. `REJECTED` preserves a stable projection category. Provider and
rate-limit exceptions remain visible as normalized aggregate failures.

## Future integration guard

A successful measurement will not itself authorize persistence. A later audit
must decide how repaired-source provenance is carried into checkpoint, report,
and stored-candle evidence before any retry. Automatic repair must remain
explicit and observable for future series; it must never become an unrecorded
fallback. A rejected or failed measurement leaves batch 19 and batch 20 blocked.

## Verification target

The implementation package must add focused happy-path and failure-path tests
for binding validation before provider access, the exact `repair=True` request,
strict projection rejection, rate-limit/provider failure normalization, report
redaction, atomic output, and the absence of persistence dependencies.

Package verification: 74 focused Yahoo/diagnostic/architecture tests passed;
the complete suite passed with 3,012 tests, four skips, and one existing
Starlette deprecation warning; `git diff --check` is clean.
