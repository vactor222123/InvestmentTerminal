# Phase 7 — Yahoo corporate-action collection

Classification: `IMPLEMENTATION`. Fresh GitHub `develop` clone, exact clean
baseline `58905a9c0e1fe97cd972f55c2f6c926eaef62b80`.

## Decision and focused audit

The user explicitly paused EODHD evaluation and asked to finish the dividend and
split topic using the existing Yahoo direction. This supersedes the *next-step
selection* in the earlier source-comparison/provenance audits; it does not turn
unknown provenance or data rights into verified facts. Existing EODHD code stays
available as an inactive experiment. No subscription or migration was made.

The existing `YahooPriceBasisClient` obtains normalized action columns, but its
qualifier discards their values after counting. Candle storage and research
exports contain no action observations. Thus another count-only qualification
would not close the acquisition/storage gap. The selected smallest coherent
vertical change is collection, typed validation, separate durable snapshot,
redacted reporting and offline repeat/recovery, with a bounded live check in the
same delivery. No existing JSON contract or SQLite schema changes.

## Source semantics

Inspected installed and locked yfinance 1.6.0 plus its
[official pinned source](https://github.com/ranaroussi/yfinance/blob/1.6.0/yfinance/scrapers/history.py)
and [public history interface](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html).
The history frame is normalized, not raw chart evidence. The library can create
zero action columns and handles ETF capital gains separately. It can also remove
dividend currency before merging actions into history; metadata quote currency
is therefore not sufficient to label cash payments. The public metadata method
may make an auxiliary five-day intraday request. The client does not claim one
HTTP call, inspect private yfinance caches, or introduce direct chart access.

Cash amounts remain exactly normalized observations with event currency `null`
and historical per-share adjustment basis unverified. A split is recorded as a
positive new-shares/old-share ratio, including reverse splits. No ratio is
applied to existing Yahoo prices. No cash event is posted to a broker ledger.
This avoids double adjustment, fabricated holdings/cash, and dividend-inclusive
return claims unsupported by the available source evidence.

## Implemented contract

- One canonical selected provider symbol, UTC-midnight `[start, end)` window,
  positive span up to 3,660 days, no future end, at most 4,000 history rows.
- Explicit `actions=True`, `auto_adjust=False`, `back_adjust=False`,
  `repair=False`, `keepna=True`, `rounding=False`, daily interval; one application
  history invocation followed by public metadata lookup on the same ticker.
  No application retry loop, no mass scan.
- Exact metadata-symbol equality, explicit quote-currency code (case retained:
  `GBp` is not converted to `GBP`), known timezone and EQUITY/ETF/MUTUALFUND type.
- Unique ascending timezone-aware history index, exact window, no duplicated
  exchange-local dates. Both dividend and split columns are mandatory; optional
  capital gains are retained with a separate presence flag.
- All action values must be finite numeric nonnegative values, never bool/text.
  Nonzero events are positive; a split ratio of one is rejected. No incomplete
  action row is omitted. Zero observations do not certify absence of events.
- Typed frozen models, deterministic timestamp/kind ordering, UTC persistence
  plus local session dates, strict schema and canonical content checksum.
- Action extraction intentionally does not depend on finite OHLCV values. A
  malformed price cannot erase a valid event, and this module exports no prices.
- Source layer and raw-source completeness remain explicitly unknown. An absent
  capital-gains column is visible even if the observed capital-gain count is zero.

## Persistence and repeat behavior

Private snapshot and redacted report are separate files with explicit paths.
Both destinations are cooperatively locked before provider work; aliasing,
cache/output overlap and existing reports fail preflight. A stale lock is not
automatically deleted: first confirm no run is active. This is a single-operator
local command, not protection against unrelated external file editors.

The private snapshot is atomically written, reopened, strictly reconstructed
and checked before `STORED` is reported. Existing matching snapshots are
revalidated and reused **without provider work**, preserving exact bytes and
fetch time. Duplicate JSON keys, invalid schema/checksum, different symbol/window
and corrupt snapshots fail without overwrite or network fallback. File reads
are limited to four MB. Reports contain only aggregate evidence and fixed error
categories; paths, identities, values and provider messages remain outside them.

Snapshot and report are not a two-file transaction. If report writing fails,
retain the snapshot and rerun with the same snapshot path and an unused report
path; validated reuse recovers the report offline. A failure after snapshot
replacement is reported as failed, with file presence visible, not rolled-back
success. Never delete prior evidence to make a retry succeed.

For an actual refresh choose a **new** snapshot path and the full required
window. Cash-action history may be revised, so this implementation never merges
an incrementally fetched tail into older normalized observations. Content hashes
exclude fetch time to compare unchanged content; exact-file hashes bind each
acquisition. Selection of a latest snapshot is explicit, not inferred from its
filename. Broad weekly action orchestration is not implemented here.

## Measured verification

Local focused suite:

```text
python -m pytest tests/test_yahoo_corporate_actions.py tests/test_yahoo_price_basis_qualification.py tests/test_architecture_dependencies.py tests/test_dependency_reproducibility_contract.py --basetemp=.pytest-actions-focused -q
111 passed
```

Full regression: `3423 passed, 4 skipped`, one existing Starlette warning.
`git diff --check`: passed at package delivery.

One workspace-only public AAPL acquisition requested 2016-10-01 inclusive to
2026-10-01 exclusive. It returned `STORED`, 2,512 normalized history rows,
40 dividend observations, one split and no observed capital gains (column
absent). It used no private runtime input and opened no SQLite database.

Exact-file snapshot SHA-256:
`c39053b90d4439cc540beea0d7e471fb5caffbb82115de2ce883dafa95f2134f`

Normalized-content SHA-256:
`b7f8b4aa6e5853628477c3429156df9d8019da6d4f54ba6492342c0cdd88c8a7`

The second invocation omitted the cache argument and reused the existing
snapshot offline: `reused_snapshot=true`, both hashes unchanged. Source values,
workspace operational files and cache are excluded from Git and the ZIP.
This proves the measured collection/reuse path, not source completeness, payout
currency, adjusted-return accuracy or all-instrument operational readiness.

## Using the delivered command

After applying and committing the package, inspect `--help`. A selected-symbol
acquisition requires `--symbol`, `--start`, `--end`, `--snapshot-output`,
`--report-output`, and an explicit writable `--cache-directory`. No hand-entered
dividend or split data is needed. Use runtime data for the private snapshot and
runtime reports for the redacted result. For offline repeat use the same
snapshot and a new report path; omit the cache argument to avoid ambiguity.

SEND: only the `YAHOO_CORPORATE_ACTION_COLLECTION` redacted report.

DO NOT SEND: private action snapshot, portfolio, database or provider cache.

No user runtime execution is required to repeat this already measured public
workspace test. The next operational step is package application and commit.
Next development: consume the validated snapshot in the generic instrument
research export with visible scope, unknown currency/basis and missing/stale
evidence. The acquisition/storage topic is delivered at this bounded scope;
cash/total-return accounting and full-universe action refresh remain separate
features, not hidden claims of completion.
