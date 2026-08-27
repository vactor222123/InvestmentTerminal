# Phase 7 Package 56 - Resumable Batch-Ingestion Boundary Audit

## Classification

AUDIT.

## Existing facts

`YahooFinanceClient.get_candles()` owns bounded Yahoo OHLCV requests.
`HistoricalMarketService.import_candles()` composes it with idempotent
`CandleRepository.save_many()` persistence.

`MarketDataRefreshService.ensure_many()` is not the required bootstrap
boundary: it uses a three-year initial lookback, stops at the first item
failure, and has no CLI, durable checkpoint, or restart contract.

## Selected implementation boundary

Add one sequential service and CLI that compose existing Yahoo, database,
repository, historical import, and atomic JSON boundaries. Its private
schema-version-1 request contains resolution, aware UTC start/end, and 1-20
unique symbol/currency items.

Items are normalized and sorted deterministically. Failures are caught per
item and later items continue. Each successful symbol commits independently;
provider I/O must not be held in a cross-symbol SQLite transaction.

## Resume contract

A private mutable checkpoint is written atomically after every completed item.
It contains a canonical request SHA-256 and private per-symbol outcomes. It is
reusable only when version and checksum match exactly. Terminal `SUCCESS` or
`EMPTY` items are skipped on restart; failed items are retried.

If execution stops after a database commit but before checkpoint publication,
the symbol is downloaded again. Existing repository idempotency makes this
safe and the next checkpoint reconciles progress.

The separate redacted report contains timing, aggregate item counts,
downloaded/inserted/duplicate totals, status, and normalized failure types. It
excludes symbols, paths, prices, provider text, and exception messages.

Statuses are `SUCCESS`, `PARTIAL`, and `FAILED`. Checkpoint-write failure stops
immediately because resumability evidence is no longer trustworthy.

## Excluded scope

Concurrency, retry/backoff policy, scheduler, universe acquisition, calendar
generation, indicators, valuation, and mass ingestion remain excluded.

## Selected next package

Implement request/checkpoint/report models, sequential service, CLI, focused
continuation/failure tests, and architecture guards. Then qualify 10-20
instruments over ten years before S&P 500 expansion.
