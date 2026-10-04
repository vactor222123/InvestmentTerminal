# Phase 7 — Yahoo price-basis semantics and provenance audit

Classification: `AUDIT`. A fresh clean GitHub `develop` clone matched
`b25f437c0009bca1dcade99b269650716b30e4c3`. No new Yahoo history
request, private export, runtime database, or candle mutation was made. The
previous one-instrument schema-1 report remains immutable.

## Evidence inspected

The repository locks `yfinance[repair]==1.6.0` in both dependency locks; the
local installed version is also 1.6.0. The one-instrument qualifier calls
`Ticker.history(interval="1d", auto_adjust=False, actions=True,
repair=False, raise_errors=True)` and validates the returned DataFrame, not
the raw Yahoo chart response. The previous MCD report had 251 rows and
`QUALIFIED` field shape; this audit did not repeat that request.

The [pinned yfinance 1.6.0 quote parser](https://github.com/ranaroussi/yfinance/blob/1.6.0/yfinance/utils.py)
sets `Adj Close` equal to `Close` when the Yahoo `adjclose` indicator is
absent. Its [history assembly](https://github.com/ranaroussi/yfinance/blob/1.6.0/yfinance/scrapers/history.py)
adds `Dividends` and `Stock Splits` columns filled with zero when no matching
events are parsed, and applies exchange-local daily dates. Consequently,
presence and finite values in the normalized DataFrame do **not** prove
presence of those fields or completeness of actions in the raw Yahoo
response. This is the decisive limitation of schema 1: `QUALIFIED` means
only **yfinance-normalized frame shape qualified**.

[Yahoo's adjusted-close explanation](https://in.help.yahoo.com/kb/adjusted-close-sln28256.html)
describes backward adjustments for applicable splits and dividend
distributions. That definition does not validate any particular downloaded
row, dividend currency, ETF capital-gains distribution, or investor-specific
total return. The pinned yfinance history implementation processes `Capital
Gains` for `ETF` and `MUTUALFUND` instrument types, but the current qualifier
does not inspect that candidate column or record instrument type. The
[yfinance repair documentation](https://ranaroussi.github.io/yfinance/advanced/price_repair.html)
also documents missing/bad dividend or split adjustments and currency-unit
errors; this request deliberately used `repair=False`. With default
`keepna=False`, yfinance may also drop all-zero/NaN rows. Therefore the 251
returned rows are not an exchange-session completeness verdict.

## Terminal boundary and decision

`Candle` and the SQLite `candles` table store OHLCV and currency, but no
adjusted close, action, source version, adjustment policy, or exchange-local
session key. The existing research export labels its basis
`STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`. Do not reinterpret stored `Close` as
unadjusted transaction price or adjusted total return, overwrite it, add a
column to the existing candle JSON, or calculate dividend-inclusive returns
from the schema-1 qualification. The current `provider_identity` field names
Yahoo but does not expose the yfinance normalization layer or whether a value
was synthesized.

The smallest next implementation is a **separate schema-2 redacted
qualification**, preserving schema 1 and all candle/storage contracts. It
should explicitly identify the observed layer as `YFINANCE_HISTORY_FRAME`,
record the pinned yfinance version and request flags, and label raw-source
field presence/action completeness as `UNKNOWN` rather than inferred from
DataFrame columns. Keep one-symbol/one-history-call bounds, aggregate-only
output, and fake-provider failure/privacy tests. Do not claim schema 2 solves
raw-source provenance. A later explicit evidence design would need source
identity/version, quote currency and exchange-local session mapping, action
types and units, raw-versus-synthesized indicators, request/repair policy,
acquisition time and checksum, and separate completeness/quality evidence.
Only after those are measured and reviewed should adjusted-price persistence
or return calculation be selected. No bulk qualification or scheduler is
authorized by this audit.
