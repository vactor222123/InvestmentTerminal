# Phase 7 — price-source evidence and access audit

Classification: `AUDIT`. A fresh, clean GitHub `develop` clone matched
`6226425f466986a0c79567611b70baa8e14707c7`. This single package
combines three related gates: the existing technical boundary, the published
source/access terms, and the smallest safe next decision. It makes no new
provider request and accesses no private runtime files.

## 1. Technical boundary observed

`YahooPriceBasisClient.get_daily_frame` makes one yfinance `Ticker.history`
call with `auto_adjust=False`, `actions=True`, and `repair=False`. The
qualification and schema-2 provenance report inspect its returned pandas
frame. They do not receive or checksum the Yahoo chart response bytes, and
schema 2 deliberately marks five raw-source facts `UNKNOWN`. The latest
one-symbol MCD report measured 251 normalized rows and four nonzero dividend
entries; it does not resolve any of those raw-source facts.

The [pinned yfinance quote parser](https://github.com/ranaroussi/yfinance/blob/1.6.0/yfinance/utils.py)
can substitute `Close` for absent raw `adjclose`; its
[history assembler](https://github.com/ranaroussi/yfinance/blob/1.6.0/yfinance/scrapers/history.py)
can create zero-filled action columns. Thus the frame cannot distinguish a
source field from a synthesized value. The existing OHLCV candle store has no
adjustment/action provenance, and the research export identifies its price
basis as `STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`. A direct chart-response
collector would be a new provider-access and retention boundary, not a
small extension of the current normalized-frame qualifier.

## 2. Published access terms and unresolved authority

The [yfinance project notice](https://github.com/ranaroussi/yfinance/blob/main/README.md?plain=1)
says it is not affiliated with Yahoo, directs users to Yahoo's terms for
rights in downloaded data, and characterizes the Yahoo Finance API as
intended for personal use. That notice is not a data licence from Yahoo.

The current [Yahoo Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)
include restrictions on automated collection without express prior
permission, access outside Yahoo-provided interfaces/instructions, and
creating a database or archive that competes with or materially substitutes
for Yahoo or its data providers. These clauses do **not**, by themselves,
establish that every private local cache is prohibited; nor does the
repository contain evidence of permission or a licence covering the proposed
raw chart-response capture, long-term retention, and onward sharing. The
[Yahoo Developer API terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html)
have not been established as applicable to the undocumented chart access
used through yfinance. This is a scope/authority uncertainty, not a legal
conclusion about the user's existing installation.

## 3. Decision and next bounded work

Do not implement a new direct Yahoo chart client, raw-response archive,
adjusted-price/action SQLite schema, inferred total-return calculation, or
bulk qualification on this evidence. Preserve schema 1, schema 2, current
OHLCV, and all JSON contracts. This does not retroactively certify or
adjudicate the existing raw-close collection workflow.

The next package should compare **documented, authorized** historical
price/corporate-action sources against the Terminal's concrete needs:
ten-year daily coverage and instruments, adjusted-close/action definitions,
currency and exchange-session mapping, permitted access rate, local storage,
derived indicators, and whether private output may be shared for ChatGPT
analysis. Record the provider's actual contract or written permission,
not an inferred right from public availability. If that evidence is obtained,
first build a one-instrument, redacted source-provenance qualification with
source/version, raw-versus-derived field flags, action types/units, currency,
session mapping, acquisition time, and checksum; test absent/malformed fields
and permission/transport failures before selecting persistence. Meanwhile
the existing raw-close indicator pipeline remains a separately scoped product
path; do not relabel it as adjusted or total-return data.
