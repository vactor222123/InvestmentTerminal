# Phase 7 Package 16 — Single-Instrument Refresh Observability

Baseline: `develop @ 01b8a88c9030e168159c66a5bc51c644fab153a0`.

This package adds `investment_terminal.cli.market_data_refresh`, a bounded
composition root over the existing Yahoo client, candle repository,
`MarketDataFreshnessService`, and `MarketDataRefreshService`.

The command requires explicit symbol, resolution, currency, checked-at,
database, cache, and output values. Its atomic schema-version-1 report records:

- provider and normalized request identity;
- start/completion timestamps and measured duration;
- `SUCCESS`, `NOT_READY`, or `FAILED` status;
- the existing refresh result with before/after freshness;
- exact downloaded, inserted, duplicate, and stored-total import evidence;
- a normalized visible failure when composition fails.

`NOT_READY` exits non-zero even when the provider call returned normally. This
prevents a completed refresh attempt from being presented as fresh evidence.
Provider and database failures are atomically reported before non-zero exit.

Focused tests cover stale-to-fresh success, already-fresh provider bypass,
provider failure, database failure, and a refresh that remains stale. The
package does not add scheduling, retries, multi-instrument refresh, mass
ingestion, analysis, or trading authority.

The next separate operational step is one live MSFT run at an explicit
checked-at time. Its report must be reviewed before another instrument or any
broader refresh is authorized.

Verification:

```text
focused: 69 passed
full: 2,731 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
