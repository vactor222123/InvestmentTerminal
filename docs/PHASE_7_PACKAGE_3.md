# Phase 7 Package 3 — Bounded Yahoo Candle Ingestion

## Verified baseline

`develop @ e1d6571ecb4abaa53bb39b4630975d70e790f646`

## Selection evidence

The user-executed qualification returned `SUCCESS` for MSFT daily data: 12
candles covering 2026-08-03 through 2026-08-18. This proves only that bounded
request and permits one persisted trial.

## Implemented boundary

`investment_terminal.cli.yahoo_candle_ingestion` accepts one instrument and
half-open interval plus explicit cache, SQLite, and report paths. It reuses the
Yahoo client, historical service, and candle repository, initializes the
existing schema, and atomically exports `SUCCESS`, `EMPTY`, or `FAILED`.

`Database` accepts an optional explicit path while retaining the existing
`Settings.DATABASE_PATH` default for current callers.

## Limits and next action

No batching, scheduling, retries, provider switching, coverage claims,
analysis, AI, broker access, or trading were added. Run one bounded local
ingestion and inspect its stored counts before selecting broader ingestion.
