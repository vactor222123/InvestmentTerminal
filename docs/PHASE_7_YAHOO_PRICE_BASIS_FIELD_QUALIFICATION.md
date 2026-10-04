# Phase 7 — Yahoo price-basis field qualification

Classification: `IMPLEMENTATION`. Fresh clean GitHub `develop` matched
`dd8c32a83eaa8ba7c341d2cf766a510942393b94` before edits.

The separate `yahoo_price_basis_qualification` command takes one explicit
symbol and a positive, at-most-3660-day UTC-date window. It makes exactly one
daily yfinance history request with `auto_adjust=False`, `actions=True`,
`repair=False`, and `raise_errors=True`. It does not use the candle repository,
SQLite, existing Yahoo ingestion projection, research export, or private
portfolio. Its only output is a new schema-1 aggregate report; the provider
may use the explicitly supplied runtime cache directory.

The report contains no symbol, OHLCV/adjusted values, event dates, local
paths, raw provider text, or exception message. It records row count and
presence, valid count, and nonzero count for candidate `Adj Close`,
`Dividends`, and `Stock Splits` columns. `QUALIFIED` means all three columns
were present with finite values in a unique, ascending, timezone-aware index
inside the requested half-open UTC window. It does **not** establish how
Yahoo adjusted prices, whether a dividend or split was economically
correct, any instrument's session completeness, or a total return.
`MISSING_FIELDS`, `MALFORMED`, `EMPTY`, and `PROVIDER_FAILURE` are distinct
statuses. Failure details use fixed categories only.

The command refuses to overwrite a report and exits nonzero unless status is
`QUALIFIED`. For one user-selected live instrument, run after applying this
package in the normal local checkout (ASCII-only PowerShell):

```powershell
python -m investment_terminal.cli.yahoo_price_basis_qualification `
  --symbol MCD `
  --start 2025-10-01 `
  --end 2026-10-01 `
  --cache-directory C:\runtime\cache\yfinance `
  --output C:\runtime\reports\yahoo_price_basis_mcd_001.json
```

Use a new output path if that report already exists. Return only the redacted
report, not the private instrument export or raw provider response. The next
decision is a separate provider-methodology and provenance audit before any
adjusted-price/action storage or return calculation. Calendar evidence and
weekly scheduling remain separate gates. No bulk qualification is requested.
