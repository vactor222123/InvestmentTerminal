# Phase 7 Package 94 — Market-Batch Construction Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`91178bd88a5b7ba4918f742afadee2df8e9d3ff3`.

## Result

The repository has enough verified evidence to construct ingestion requests,
but it does not yet contain a checksum-bound constructor joining that evidence.
The next safe package is therefore a private manifest builder, not candle
ingestion.

The established private eligibility-success projection contains 12,020 unique
Yahoo symbols. The completed schema-version-2 currency checkpoint has 12,019
`SUCCESS` outcomes and one terminal `INVALID_RESPONSE`. Construction must use
only those 12,019 successful outcomes and must preserve the single exclusion in
its redacted report.

## Existing contract

`MarketBatchRequest` schema version 1 already carries `currency` per item. A
request may contain between 1 and 20 unique symbols, accepts only `D`, `W`, or
`M` resolution, sorts items deterministically, requires an aware half-open
`start`/`end` window, and derives a canonical SHA-256 checksum. Mixed currencies
inside one request are therefore supported; currency grouping would add an
unnecessary policy.

`ResumableMarketBatchService` binds one checkpoint to one request checksum and
indexes outcomes by symbol. Consequently every generated request needs its own
checkpoint at execution time. Existing resume semantics must not be broadened
inside the constructor.

## Selected boundary

The next implementation should accept the private eligibility-success
projection, its expected checksum, the completed schema-version-2 currency
checkpoint, and explicit resolution/start/end values. It must:

1. validate both evidence checksums and require complete terminal currency
   coverage;
2. join by the exact normalized Yahoo symbol and reject unknown, missing, or
   duplicate keys;
3. retain only `SUCCESS` outcomes with valid three-letter currencies;
4. sort items by `(symbol, currency)` and partition consecutive items into
   chunks of at most 20;
5. emit a versioned private manifest containing canonical schema-version-1
   market-batch requests and a checksum over the entire manifest;
6. emit a separate privacy-safe report with counts, checksums, batch-size
   bounds, and exclusion categories, but no symbols, currencies, paths, prices,
   or provider text.

For the measured 12,019 successes, a 20-item cap implies 601 requests: 600 full
requests and one 19-item request. This is a deterministic planning fact, not
authorization to execute those requests.

## Failure paths

Construction must fail closed for checksum mismatch, incomplete or legacy
currency evidence, symbol-set mismatch, malformed successful currency, an
unsupported resolution, invalid dates, or an empty success set. It must not
contact Yahoo, create batch checkpoints, retrieve candles, modify SQLite, or
schedule mass ingestion.

The first operational use after implementation must generate and inspect only
the private manifest plus its redacted aggregate report. A separate later
package must authorize a bounded ingestion slice; complete mass ingestion is
not authorized by this audit.
