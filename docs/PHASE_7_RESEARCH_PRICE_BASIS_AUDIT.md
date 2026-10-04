# Phase 7 — research price-basis and readiness audit

Classification: `AUDIT`. A fresh clean GitHub `develop` clone matched
`ef67204bbae7eea0ea77d5f9e582138219397f29`. No private export,
operational SQLite database, provider response, or runtime source was read or
changed. The user explicitly allowed sharing the verified private MCD export
if useful, but this audit does not use that permission or upload anything.

## Actual boundary

The existing MCD redacted report records 2,512 stored daily-labeled rows and
raw-close SMA50/SMA200 availability. The local private/report verifier checks
identity and internal parity; neither it nor the report validates provider
adjustment semantics or exchange-session coverage.

`YahooFinanceClient.get_candle_projection` requests yfinance history with
`auto_adjust=False`, `actions=False`, and `repair=False`. Its strict projection
requires `Open`, `High`, `Low`, `Close`, and `Volume`, then stores `Close` as
`Candle.close_price`. It does not project a separate adjusted close, dividend,
or split field. `Candle` and the `candles` SQLite table likewise contain only
OHLCV, symbol/resolution/timestamp, and currency. The latest indicator and
instrument research export explicitly label their basis
`STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`; the export computes raw-close SMA values
but no adjusted return. Historical session comparison exists as a separate
explicit-calendar service, but the research export carries no calendar
identity, expected sessions, or missing-session verdict.

Consequently, sharing the current private export would permit only a bounded
description of its stored raw-price path. It would not by itself meet the
user's broader objective of reliable return/performance comparison across
stocks and ETFs, including dividend and split effects. A row count or apparent
ten-year window also cannot prove complete trading-session coverage. No
corporate action, return, or missing session is inferred from absent data.

## Selected smallest next implementation

Add a **separate generic, read-only one-instrument Yahoo price-basis
qualification**, leaving the existing strict ingestion, `Candle`, SQLite,
latest-indicator, and research-export JSON contracts untouched. The command
must take an explicit symbol and bounded UTC window, make at most one provider
history request with adjustment disabled and actions requested, and inspect
only whether candidate adjusted-close/dividend/split fields are present,
well-formed, timestamp-aligned, and finite where applicable. It must report
missing, malformed, and provider-failure cases distinctly through a new
versioned redacted aggregate report, without exposing identity, values,
paths, raw provider text, or exception messages. It must not save adjusted
prices, reinterpret existing raw candles, calculate returns, or claim that a
present field establishes an authoritative adjustment methodology.

Focused fake-provider and failure-path tests should cover column absence,
non-finite or duplicate/misaligned rows, malformed actions, provider errors,
privacy, and no writes. After implementation, one explicitly selected live
instrument may qualify the provider shape. Only then audit provider semantics
and choose an end-to-end versioned storage/provenance contract for adjusted
prices and actions. Exchange-specific calendar evidence and per-series
session completeness remain separate gates. No bulk provider run, automatic
private sharing, return calculation, or weekly scheduler is authorized here.
