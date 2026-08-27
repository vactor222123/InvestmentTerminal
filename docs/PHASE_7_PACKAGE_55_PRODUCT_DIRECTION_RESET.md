# Phase 7 Package 55 - Product Direction Reset

## Classification

AUDIT.

## User outcome

InvestmentTerminal must turn one private portfolio input into an automatically
maintained, analysis-ready factual dataset. The user supplies portfolio
transactions or broker evidence. The Terminal acquires remaining market data
from internet providers, persists it, computes deterministic measurements, and
exports evidence that ChatGPT can analyze separately. The Terminal does not own
final investment conclusions or autonomous trading.

## Repository evidence

Implemented foundations include bounded Yahoo candle ingestion, idempotent
SQLite persistence, freshness and coverage checks, SMA20/50/200, EMA20, RSI14,
MACD, ATR14, Bollinger Bands, transaction import, position reconstruction,
realized/unrealized performance, valuation history, and maintained-universe
contracts.

Operational evidence remains narrow: five-year daily history exists for MSFT,
AAPL, and IBM only. Refresh accepts one explicit symbol. No production batch
orchestrator, automatic broad-universe provider, resume checkpoint, scheduler,
or ten-year broad-universe measurement exists.

## Product correction

Phase 7 primary work is reset to:

```text
portfolio transactions
-> automatic instrument resolution with unresolved-item isolation
-> versioned maintained universe
-> resumable ten-year multi-instrument ingestion
-> incremental refresh
-> deterministic indicators and portfolio valuation
-> ChatGPT-ready factual export
```

Ticker and metadata failures are per-instrument outcomes and must not block
unrelated instruments. The OpenFIGI/Yahoo single-instrument remediation chain
becomes secondary. Existing recommendation and grounded-AI code is preserved
but is not on the critical MVP path.

The working target is ten years of daily OHLCV. Qualification starts with
10-20 instruments before expansion to a maintained S&P 500 and representative
ETF universe. It must measure coverage, repeat idempotency, bounded provider
load, isolated failures, and resumability.

## Next package

Audit the smallest resumable batch-ingestion boundary that composes existing
Yahoo, repository, and report contracts. Do not implement a scheduler, mass
run, new indicator framework, recommendation logic, or more single-ticker
remediation in that audit.
