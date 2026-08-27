# Phase 7 Package 59 - Automatic Maintained-Universe Source Audit

## Classification

AUDIT.

## Product requirement

The user must not maintain a broad symbol list manually. InvestmentTerminal
must acquire a current, versioned universe from an internet source, preserve
source evidence, normalize provider symbols deterministically, and only then
compose a market batch request.

## Source findings

S&P Dow Jones Indices is authoritative for the S&P 500 and publishes current
index characteristics and constituent presentation. The official page reports
503 constituents, reflecting multiple share classes for some companies. The
public web presentation does not establish a stable documented machine API for
the complete list. Scraping an undocumented endpoint would create an unstable
contract and may create licensing ambiguity.

State Street publishes official daily holdings for the SPY ETF. SPY seeks to
track the S&P 500, and its official fund page exposes daily holdings download.
Fund holdings are an investable, current, machine-readable broad-US-equity
universe, but they are not legally or semantically identical to the proprietary
index constituent list. Cash, derivatives, timing differences, and tracking
operations may differ.

Selected source identity:

```text
STATE_STREET_SPY_DAILY_HOLDINGS
```

Selected universe identity:

```text
SPY_FUND_HOLDINGS
```

The implementation must never label this evidence `SP500_INDEX_CONSTITUENTS`.

Official references:

- https://www.spglobal.com/spdji/en/indices/equity/sp-500/
- https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy

## Selected implementation boundary

Add a bounded State Street holdings client, exact raw-byte archive, typed CSV
parser, normalized universe document, and redacted qualification report.

Required evidence:

- source identity and requested URL identity;
- retrieval and source `as_of` timestamps;
- exact archive SHA-256;
- normalized document schema/version;
- source row, accepted equity, excluded non-equity, unique source ticker, and
  unique Yahoo-symbol counts;
- normalized failure type without provider body or exception message.

The parser must fail closed on missing required headers, invalid dates,
duplicate accepted tickers, empty equity holdings, or implausible bounded
coverage. The first qualification bound is 450-550 unique accepted equities.

## Symbol projection

Preserve the exact source ticker. Produce a separate Yahoo symbol projection.
The initial normalization is intentionally narrow: trim/uppercase and replace
the single class-share separator `.` with `-` (for example, `BRK.B` becomes
`BRK-B`). Reject rather than guess unsupported ticker syntax. Currency defaults
must not be inferred from the holdings file unless the source supplies it.

## Persistence and privacy

Archive exact source bytes immutably before normalized publication. Write the
normalized universe atomically. Raw holdings and normalized member identities
remain operational evidence and are not included in delivery ZIPs. The
shareable report exposes only aggregates, provenance identity, timestamps, and
checksums.

## Excluded scope

- undocumented S&P endpoint scraping;
- claiming exact proprietary index membership;
- maintained ETF product-list acquisition;
- automatic batch-request composition;
- market ingestion, scheduler, concurrency, indicators, or valuation.

## Selected next package

Implement and hermetically test the bounded SPY daily-holdings qualification.
One controlled live qualification must be reviewed before its members can feed
the resumable market batch.
