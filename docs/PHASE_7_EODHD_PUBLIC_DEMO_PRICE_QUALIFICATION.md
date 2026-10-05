# Phase 7 — public EODHD ETF price-shape qualification

Classification: `IMPLEMENTATION` with one bounded public operational check.
Fresh GitHub `develop` matched the exact clean
`d02a65c3f8026b98e5a230f2c4b1361ec688b5db` baseline before changes.
The [EODHD EOD API](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes)
documents a public `demo` token for `VTI.US`, raw OHLC, dividend/split-adjusted
close, daily dates, and inclusive provider window endpoints. Its
[personal-use terms](https://eodhd.com/financial-apis/terms-conditions) do not
authorize sending source values to third-party AI; this package sends none.

## Boundary implemented

`python -m investment_terminal.cli.eodhd_demo_price_qualification` accepts
an explicit exclusive-end date window of at most 3,660 days and a new report
path. Symbol `VTI.US`, the public `demo` token, JSON format, daily period and
ascending order are fixed in the client. The client makes at most one GET,
converts the exclusive end to EODHD's inclusive `to` date, caps the response
at 4 MB, and retains body bytes only in memory. No private credential, raw
response archive, candle/SQLite write, adjusted-return calculation, or
existing JSON migration is involved.

The separate schema-1 report is aggregate-only: exact source-byte SHA-256,
row count, first/last dates, field-presence counts, and stable failure codes.
It never includes source prices, volume values, response body, request URL,
exception text, or a private token. Its `QUALIFIED` state means only that a
strict JSON array had ordered in-window dates and structurally valid daily
fields. It does not prove currency, MIC, corporate-action completeness,
adjustment accuracy, exchange-session completeness, or total return. HTTP,
transport, malformed/duplicate-key/nonstandard JSON, missing fields,
nonfinite/invalid values, date/order/window, size, and atomic report-write
failure paths are covered by focused fake-provider tests.

## One public measurement

One live `VTI.US` `demo` EOD request was made for `[2016-10-01,
2026-10-01)`. Its redacted report records `QUALIFIED`, 2,512 daily rows,
first date `2016-10-03`, last date `2026-09-30`, and all seven required fields
present in all 2,512 rows. Exact source-response SHA-256:
`5b724f87af8897f30abc05fd7917141cddbe7e909fa62de2f87a589b1e581a14`.
Exact redacted-report SHA-256:
`a7b68c75de025607123c25c1c6ace018b3d0b8f4f717d5b8221c21b464ccbf86`.
The report remains untracked in the isolated checkout at
`.operational-eodhd-demo-vti-report.json` and is excluded from the package
ZIP. No source values were printed or persisted, and `C:\runtime` was not
accessed.

After that one live call, local-only strict duplicate-key/nonstandard-number
and fractional-volume guards were added and tested; no second live request
was made. Thus the measured result belongs to the pre-hardening build of the
same qualifier, while the final hardened parser is supported by fake-client
tests, not by a repeated live observation.

## Next gate

Before considering persistence, qualify one public `VTI.US` dividend and
split response through the separately documented action endpoints, with
source-byte provenance, action units/currency, redacted counts and failure
paths. Then review whether ETF distributions/capital gains and instrument
identity can actually be established. A paid subscription, bulk EOD fetch,
provider switch, adjusted-price store, or ChatGPT value upload requires a
separate explicit decision and applicable rights; the one-ETF demo cannot
establish any of them.
