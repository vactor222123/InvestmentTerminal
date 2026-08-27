# Phase 7 Package 52 - Automated Private Ticker Resolution Audit

Package type: `AUDIT`.

Source baseline: `develop @ 0af31050fc29e7c675fb2e34399adcbd8f180d8a`.

## User Requirement

Instrument identity, venue, and ticker evidence must be obtained automatically
from network providers. The operator must not manually transcribe a ticker or
make an unsupported provider-row selection.

## Factual Repository State

- The private transaction identity already supplies an ISIN.
- The local OpenFIGI diagnostic already preserves the candidate and all
  returned provider tickers without exposing them in the shareable report.
- OpenFIGI mapping supports `micCode`, `exchCode`, and currency filters, but the
  current private quote contract does not contain an independently verified MIC
  or intended venue.
- The runtime already pins `yfinance` and uses Yahoo for candle acquisition.
- Installed `yfinance.Search` exposes normalized quote search results through
  `quotes`, including provider symbols and associated descriptive fields.
- The documented `yfinance.Search` query contract names ticker symbol or company
  name, not ISIN. Repository tests therefore cannot claim live ISIN-search
  behavior without a bounded operational qualification.
- No public, officially documented Trade Republic developer API is present in
  the repository or available as a stable authority for this lookup.

Primary provider references:

- `https://www.openfigi.com/api/documentation`
- `https://ranaroussi.github.io/yfinance/reference/api/yfinance.Search.html`

## Selected Boundary

The smallest safe next implementation is a Yahoo ISIN-search qualification,
not a manual decision form and not an automatic quote rewrite.

It must:

- read one ISIN from the existing private candidate-absence diagnostic;
- execute one bounded `yfinance.Search` request with news, lists, research,
  navigation, fuzzy search, and recommendations disabled;
- preserve normalized Yahoo quote candidates in a separate private atomic JSON
  artifact;
- emit a redacted schema-version-1 report containing status, candidate count,
  unique symbol/exchange counts, timing, and privacy-safe failure only;
- expose no ISIN, symbol, exchange, provider text, path, or raw response in the
  shareable report or stdout;
- perform no quote, metadata, transaction, qualification, or valuation mutation.

## Acceptance for Later Automated Resolution

Yahoo ISIN search is operationally usable only if the bounded live result is
non-empty and deterministic enough to identify candidate symbol/exchange rows.
The later resolver must cross-check those rows with the already archived
OpenFIGI listing evidence. It may select automatically only when one normalized
listing remains after explicit identity, exchange, and currency rules; zero or
multiple survivors remain fail-closed.

## Required Tests

- exact private request scope and disabled unrelated Yahoo result categories;
- normalized, deterministic candidate ordering and duplicate handling;
- empty, malformed, provider-failure, and private-write-failure paths;
- atomic private candidate output;
- redacted report/stdout exclusion of all private values and paths;
- no mutation outside the explicit private output and redacted report;
- architecture/dependency guards.

## Explicitly Deferred

- live Yahoo ISIN request;
- automatic OpenFIGI/Yahoo cross-provider resolution;
- quote correction;
- another OpenFIGI rerun;
- quote qualification, valuation, Review execution, and Phase 8 UI.

## Audit Result

`IMPLEMENTATION-READY`

## Verification

- focused Yahoo/OpenFIGI/architecture checks: 45 passed;
- complete local suite: 2,815 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
