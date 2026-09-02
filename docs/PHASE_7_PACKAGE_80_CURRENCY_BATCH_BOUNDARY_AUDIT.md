# Phase 7 Package 80 — Currency and Batch Boundary Audit

## Classification and Baseline

Classification: `AUDIT`.

Fresh `develop` clone verified exactly at:

```text
92e71a121f3b8e41d698d7858a87a7caf5056cd0
```

No private runtime input was read and no provider request, batch generation, or
ingestion was executed.

## Facts Verified

The private success projection contains `source`, `source_symbol`, and
`yahoo_symbol`; it deliberately contains no currency.

The Nasdaq Trader source parser receives symbol, name, listing code, ETF flag,
test flag, and Nasdaq financial status where applicable. It receives no
currency field. Therefore the source universe cannot establish trading
currency.

Eligibility requests currently pass `USD` to `YahooFinanceClient`. The client
uses the caller value when constructing every `Candle`; it does not read or
validate response metadata currency. Eligibility success consequently proves a
validated 90-day OHLCV series, not USD currency.

`MarketBatchRequest` schema version 1 requires an explicit non-empty currency
for every symbol and permits only 1–20 unique symbols. It sorts items
deterministically and includes currency in its request checksum. No service
currently converts the 12,020-member success projection into these requests.

`ResumableMarketBatchService` checkpoints after each item and skips prior
`SUCCESS`/`EMPTY` outcomes, but failed items are retried without a typed retry
cap or immediate rate-limit stop. It is suitable for the earlier controlled
1–20 item qualification, not direct complete-universe orchestration.

The candle table uniqueness key is `(symbol, resolution, timestamp)`, while
currency is stored as a non-key attribute. A candle inserted under a guessed
currency cannot later coexist with a corrected currency for the same key, and
`INSERT OR IGNORE` would preserve the earlier row. Currency must therefore be
verified before broad ingestion.

The existing Yahoo fundamental adapter reads provider `info.currency`, but it
also performs broad fundamental normalization and silently falls back to the
caller currency when provider currency is absent. It is not a fail-closed
currency-qualification boundary. The existing Yahoo search normalization can
preserve candidate currency, but its operational service is scoped to one
private ISIN and does not establish exact symbol-to-currency coverage for a
broad universe.

## Decision

Do not infer USD from Nasdaq/other-listed membership and do not generate batch
requests yet.

The smallest safe implementation is a separate resumable Yahoo symbol-currency
qualification over the private success projection:

- exact Yahoo symbol lookup only;
- accept only one normalized exact-symbol result with a three-letter currency;
- private atomic per-symbol checkpoint bound to the projection checksum;
- bounded invocation size and deterministic pending order;
- typed terminal/retry outcomes and immediate rate-limit stop;
- separate redacted aggregate report;
- no candle retrieval, batch generation, database access, analysis, or ranking.

After controlled qualification proves the contract, a later package may
project only currency-qualified successes into deterministic 1–20 item,
ten-year daily `MarketBatchRequest` documents. Broad ingestion remains blocked
until both boundaries are implemented and operationally measured.
