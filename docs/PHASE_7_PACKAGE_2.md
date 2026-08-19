# Phase 7 Package 2 — Yahoo Historical Candle Operational Qualification

## Verified baseline

`develop @ 503717122f56680d4d7e725b2f616333a89e7a94`

## Implementation status

```text
COMPLETE
```

## Delivered boundary

Package 2 adds an immutable qualification request/result, a bounded operational
service over the existing `YahooFinanceClient`, and a CLI with atomic JSON
export:

```text
python -m investment_terminal.cli.yahoo_candle_qualification
```

The service validates exact symbol, resolution, currency, half-open request
window, unique chronological candles, and measured run timestamps. It preserves
`SUCCESS`, `EMPTY`, and `FAILED` without conflating empty coverage or provider
failure with success. Failed reports are durably exported before non-zero exit.

## Explicit live qualification

One live smoke request was attempted on 2026-08-19:

```text
provider   = YAHOO_FINANCE
symbol     = MSFT
resolution = D
currency   = USD
window     = [2026-08-01T00:00:00Z, 2026-08-19T00:00:00Z)
status     = FAILED
duration   = 0.008345 seconds
failure    = APIError: Yahoo Finance historical request failed for MSFT.
coverage   = unknown
```

The complete local report remains outside source control. This failure proves
only that this request did not complete in the execution environment. It does
not prove general Yahoo unavailability and does not justify a provider change.

A fresh-clone rerun identified and resolved an implicit unwritable yfinance
cache path. With an explicit writable cache, transport then failed to connect to
`fc.yahoo.com:443`. The remediation and measured distinction are recorded in
`docs/PHASE_7_YAHOO_QUALIFICATION_RERUN.md`.

## Authority and non-scope

Package 2 does not persist market candles, begin bulk ingestion, add retries or
scheduling, qualify licensing, calculate analysis, invoke AI, access a broker,
or authorize trades. It makes no approximately 20-year or broad-universe claim.

## Next action

Run the same explicit CLI from an environment with permitted Yahoo network
access. Bulk/incremental ingestion remains blocked until at least one bounded
qualification returns `SUCCESS` and its measured coverage is reviewed.
