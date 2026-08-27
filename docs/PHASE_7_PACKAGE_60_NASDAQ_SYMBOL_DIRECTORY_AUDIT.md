# Phase 7 Package 60 - Nasdaq Symbol-Directory Universe Audit

## Classification

AUDIT.

## Corrected product boundary

The product needs a large automatically maintained research universe, not exact
membership in the proprietary S&P 500 index. Package 59's SPY-fund-holdings
direction is therefore superseded before implementation.

The selected universe is:

```text
BROAD_US_LISTED_SECURITIES
```

It is sourced from Nasdaq Trader's official symbol-directory files:

- `https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt`
- `https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt`

Nasdaq documents these files, their fields, their intraday update cadence, and
their file-creation timestamp row. `nasdaqlisted.txt` covers Nasdaq listings;
`otherlisted.txt` covers NYSE, NYSE American, NYSE Arca, Cboe/BATS, IEX, and
other reported U.S. exchange listings.

Official definitions:
`https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs`.

## Selected qualification boundary

Implement one bounded client that downloads both exact public files with an
explicit timeout and stable user agent. Archive exact bytes immutably before
publishing any normalized document. Parse pipe-delimited headers by name and
validate the terminal `File Creation Time` row rather than depending on fixed
column positions.

Initial deterministic acceptance rules are deliberately limited to facts in
the official files:

- exclude `Test Issue = Y`;
- exclude non-normal Nasdaq financial status;
- require non-empty source symbol, security name, listing exchange/category,
  and ETF flag where defined;
- classify ETF versus non-ETF using the official ETF field;
- preserve all other security types rather than guessing from issuer names;
- require unique normalized listing identity and fail on symbol collision.

Warrants, rights, units, preferred shares, and other non-common instruments may
remain in the broad source universe. A later typed eligibility layer may
exclude them using verified issue-type evidence. Name-based guessing is not
authorized.

## Symbol projection

Preserve source symbol and source listing code. Produce a separate Yahoo symbol
projection with only documented transformations. Dot class separators may map
to hyphens; unsupported punctuation remains an explicit projection failure.
Projection failures are isolated and counted rather than blocking unrelated
members.

## Versioned evidence

Private schema-version-1 normalized evidence contains:

- universe/source identities;
- retrieval and both file-creation timestamps;
- exact SHA-256 for each raw archive;
- normalized source symbol, Yahoo projection, name, listing code, and ETF flag;
- explicit excluded/projection-failure records.

The redacted qualification report contains aggregate source-row, accepted,
ETF, non-ETF, excluded-test, excluded-status, projection-failure, exchange, and
collision counts plus timestamps/checksums. It excludes member identities,
names, paths, provider bodies, and exception messages.

Qualification requires both files, valid creation timestamps, no collisions,
and at least 1,000 accepted members. This lower bound detects truncated or
structurally wrong downloads without claiming a fixed universe size.

## Excluded scope

- exact S&P 500 or SPY holdings acquisition;
- name-based security-type inference;
- liquidity or market-cap filtering;
- batch-request generation;
- candle ingestion, concurrency, scheduler, indicators, or valuation.

## Selected next package

Implement the two-file client, immutable archives, typed parser/projection,
atomic private universe, redacted report, and hermetic failure-path tests. One
controlled live qualification must precede any candle request generation.
