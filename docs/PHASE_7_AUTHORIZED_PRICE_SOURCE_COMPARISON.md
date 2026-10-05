# Phase 7 — documented price/action source comparison

Classification: `AUDIT`. Fresh GitHub `develop` matched the caller's exact
`4bedf380a605bafbb6216890fdf4463b12e5c6aa` baseline; branch and worktree
were clean. Sources below were checked on 2026-10-05. This package makes no
provider request, purchase, private-runtime read, database change, or JSON
contract change. It does not adjudicate existing Yahoo-stored data.

## Product requirements used for comparison

The current gate is not merely finding an `adjusted_close` column. The source
must support approximately ten years of daily equity/ETF history, corporate
actions, instrument/exchange/currency identity, repeatable local analysis and
weekly refresh, plus an explicitly permitted route (if any) for the user's
separate ChatGPT analysis. Current Terminal candles and indicators remain
`STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`; the schema-2 Yahoo qualification has
`UNKNOWN` raw-source evidence. See
`PHASE_7_PRICE_SOURCE_EVIDENCE_AND_TERMS_AUDIT.md`.

## Official-source comparison

| Gate | EODHD | Twelve Data |
|---|---|---|
| Documented daily history | [EOD endpoint](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes) returns date, raw OHLC, adjusted close and volume for stocks/ETFs; `SYMBOL.EXCHANGE`, inclusive `from`/`to` | [Time-series API](https://twelvedata.com/docs) offers daily OHLCV and exchange/currency metadata; [date-window guidance](https://support.twelvedata.com/en/articles/5214728-getting-historical-data) caps a request at 5,000 points |
| Adjustment/action evidence | EODHD states `adjusted_close` includes splits and dividends, while raw OHLC is unadjusted; [dividend/split endpoints](https://eodhd.com/financial-apis/api-splits-dividends) are separate and include event details | [Price guidance](https://support.twelvedata.com/en/articles/5179064-are-the-prices-adjusted) says daily prices are split-adjusted; [API docs](https://twelvedata.com/docs) expose dividend/split endpoints and adjustment modes |
| Local storage | [Personal terms](https://eodhd.com/financial-apis/terms-conditions) explicitly allow a qualifying non-professional user to store, manipulate and analyze information privately and non-commercially | [Terms](https://twelvedata.com/terms) permit storage for internal use subject to tier/provider restrictions, but require data deletion within 30 days after termination or expiration, except stated exceptions |
| Third-party/ChatGPT handoff | EODHD personal terms prohibit retransmission, redistribution, display or access to information, even repackaged; no permission for uploading raw series to ChatGPT is established | Twelve Data terms require express rights for redistribution/external display; their `Derived Data` definition is not a blanket permission to send underlying prices to ChatGPT |
| Ten-year broad-universe feasibility | [EODHD pricing](https://eodhd.com/pricing) lists full-history All-World personal EOD at USD 19.99/month as checked; [free tier](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes) is limited to one historical year and 20 calls/day. Paid calls are one per symbol; the published [limit](https://eodhd.com/financial-apis/api-limits) starts at 100,000 calls/day | [Personal pricing](https://twelvedata.com/pricing) places global EOD equities/ETFs on paid Grow or above; credits and regional access are tier-dependent |

The table describes published capabilities and terms, **not** measured
coverage for the Terminal's 11,892 selected series, a recommendation to buy,
or a legal determination for the user's exact account. Price and terms may
change. A nominal call budget does not prove throughput or acceptable request
frequency. The EODHD free plan cannot validate ten-year broad-universe
history, although its published `demo` token supports full-history requests
for limited public symbols, including `VTI.US` (ETF).

## Technical implications for a bounded qualification

EODHD is the better *candidate for local-only evaluation* because its
published personal terms expressly discuss private storage and its EOD and
action APIs expose separate source fields. It is not yet selected as the
Terminal provider. A first public `demo` qualification can use one `VTI.US`
ETF window without an account or private token, inspect only aggregate field
shape and exact response checksum, and leave SQLite untouched. A separate
single-stock/split example is useful later; do not extrapolate from one ETF.

Critical safeguards before any implementation or bulk import:

1. EODHD's [EOD specification](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes)
   says `adjusted_close` is recomputed after new dividends, so old adjusted
   values may change. Never append only the tail, use adjusted values as
   stable row identities, overwrite existing Yahoo candles, or compare a
   fresh adjusted value to a cached one as automatic corruption evidence.
2. The endpoint silently defaults unrecognized `fmt`, `period`, and `order`;
   validate all request parameters locally. Its `to` date is inclusive while
   Terminal windows commonly use an exclusive end; conversion must be
   explicit. Preserve response bytes/checksum and acquisition timestamp if
   later authorized, with API tokens redacted from URLs/logs/reports.
3. The row's date and exchange suffix do not alone prove timezone, currency,
   MIC or expected trading sessions. Verify instrument mapping and action
   currencies from separate authoritative evidence; ETF distributions and
   capital-gains coverage are not established by these general docs.
4. Keep raw trade-price OHLCV, split-adjusted price, dividend-adjusted price,
   dividends/splits, and portfolio transaction cost basis separate. An
   adjusted-close series is not by itself the user's realized or total return.

## Decision gate

No purchase, credential request, provider switch, raw-series upload, adjusted
store or total-return calculation follows from this desk audit. The smallest
next technical package is a **read-only, one-public-ETF EODHD `demo`
qualification** with redacted aggregate output and failure-path tests. It can
prove response shape, dates and error behavior only, not full-universe
coverage or production entitlement. Before paid ingestion or ChatGPT value
handoff, obtain the user's provider choice and clarify with the provider the
applicable subscription, post-cancellation retention, ETF-action coverage,
and whether any specific data/derived summary may be sent to a third-party
AI service. Until clarified, keep candidate market data local and share only
non-reconstructive operational counts/checksums.
