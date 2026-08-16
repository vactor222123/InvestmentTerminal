# Phase 1 Closure — Multi-Asset Evidence Foundation

## Verified baseline

Phase 1 is closed at `develop @ d1f0f82401c1e951ae55af7e673b8c483629f3cf`.
CI run 46 completed successfully.

The roadmap scope is covered by immutable contracts for instrument identity,
exchange/currency/calendar metadata, provenance and quality, ETF
characteristics, and ETF composition. Provider integrations and Review
composition remain later integration work; they are not gaps in the Phase 1
foundation boundary.

## Phase 2 ownership boundary

The Portfolio domain owns canonical lifecycle transactions. Current portfolio
holdings remain a current-state snapshot and are not rewritten as transaction
history. History continues to own immutable Review Package evidence and must
not become the transaction-ledger source of truth.

Phase 2 begins with immutable `BUY`, `SELL`, `DIVIDEND`, and `FEE` events.
Persistence, imports, position reconstruction, realised/unrealised performance,
valuation history, and tax-lot policy follow as separate packages.
