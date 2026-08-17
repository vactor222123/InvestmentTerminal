# Phase 2 Closure — Portfolio Lifecycle Intelligence

## Verified baseline

Phase 2 is closed at
`develop @ 349620e34712fa19caeb42b0d383b6af0f661173`.
CI run 58 completed successfully.

The closure audit used `docs/ROADMAP_AFTER_AUDIT.md`,
`docs/PROJECT_VISION.md`, the current Portfolio implementation, and its tests.

## Roadmap scope evidence

| Phase 2 scope | Implemented evidence |
|---|---|
| transaction ledger | immutable transaction/ledger contracts, append-only repository, SQLite adapter |
| purchases/sales | validated `BUY` and `SELL` events, imports, CSV ingestion, position reconstruction |
| dividends | validated instrument-linked `DIVIDEND` lifecycle events |
| fees | validated `FEE` lifecycle events |
| realised/unrealised performance | deterministic average-cost realised results and quote-backed unrealised valuation |
| portfolio valuation history | immutable snapshots, append-only repository, versioned SQLite persistence |
| tax-lot readiness | explicit sale-to-acquisition selection and deterministic lot attribution |

Focused contracts cover deterministic ordering, timezone-aware timestamps,
currency isolation, immutable identities, duplicate rejection, rollback,
restart reconstruction, corrupt-payload visibility, oversell rejection, and
explicit lot-quantity conservation. The complete CI regression suite is green.

## Architecture boundary

The Portfolio domain owns lifecycle transactions, derived positions,
performance, valuation history, and tax-lot attribution. Current portfolio
snapshots remain a separate current-state representation. Canonical Review
History remains immutable review evidence and is not a transaction-ledger or
valuation-history source of truth.

No jurisdiction-specific tax disposal method is inferred. Explicit tax-lot
selection preserves human and policy ownership of that decision.

## Phase 3 entry

Phase 3 starts with a provider-neutral portfolio risk input contract. The
existing allocation and policy-gap modules are useful decision inputs, but the
repository has no canonical portfolio-level risk observation boundary.

The first package will define immutable, timestamped portfolio return-series
inputs with stable portfolio identity, explicit observation currency, unique
ordered observations, and source provenance. It will not calculate drawdown,
volatility, correlation, or recommendations. Those remain separate,
deterministic Phase 3 packages.
