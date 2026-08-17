# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint

**Current repository:** `vactor222123/InvestmentTerminal`
**Current branch:** `develop`
**Current GitHub baseline:** `e8b2f62`
**Current local package:** Phase 2 Package 11 — SQLite valuation history persistence
**Current phase:** Phase 2 — Portfolio Lifecycle Intelligence
**Current next action:** Add tax-lot readiness contracts for explicit acquisition-lot attribution

---

## Current State

Sprint 33 — Integrated Current-State Market Intelligence:

```text
CLOSED
```

A complete product alignment audit has been performed.

Phase 1 Package 1 establishes a provider-independent immutable instrument
identity contract and makes current portfolio holdings expose that contract
without changing their existing serialized JSON shape.

Phase 1 Package 2 adds explicit exchange, trading-calendar, and currency
metadata contracts and supports exchange-scoped ticker identity without
changing existing portfolio serialization.

Phase 1 Package 3 adds traceable market-metadata source provenance and
deterministic READY/PARTIAL/STALE quality assessment.

Phase 1 Package 4 adds provider-independent ETF characteristics and an
evidence envelope that preserves missing facts, source provenance, and quality.

Phase 1 Package 5 adds constituent-holding and categorical-exposure contracts
with explicit partial coverage, provenance, and quality.

Phase 1 is closed after verifying its complete roadmap scope and green CI.
Phase 2 Package 1 establishes immutable portfolio lifecycle transaction and
deterministically ordered ledger contracts without changing current snapshots.

Phase 2 Package 2 establishes append-only repository semantics and an in-memory
reference implementation with deterministic time and instrument queries.

Phase 2 Package 3 adds a versioned SQLite store and durable repository adapter
with immutable ledger metadata, strict JSON payloads, and rollback behavior.

Phase 2 Package 4 adds provider-neutral import batches and deterministic,
visible accounting for imported and duplicate transaction identities.

Phase 2 Package 5 adds a canonical provider-neutral transaction CSV schema,
line-specific validation, and lossless conversion into transaction import batches.

Phase 2 Package 6 adds deterministic open-position reconstruction from BUY and
SELL events with average-cost accounting and fail-closed oversell validation.

Phase 2 Package 7 adds deterministic realised gain/loss calculation per SELL
event and currency-safe summaries using the established average-cost method.

Phase 2 Package 8 adds quote-backed unrealised performance for reconstructed
positions with explicit valuation time, quote provenance, and currency isolation.

Phase 2 Package 9 adds immutable transaction-derived valuation snapshots and a
deterministically ordered portfolio valuation history contract.

Phase 2 Package 10 adds append-only valuation repository semantics and an
in-memory reference implementation with deterministic temporal queries.

Phase 2 Package 11 adds versioned SQLite valuation-history persistence with
immutable ownership metadata, strict JSON payloads, indexed temporal queries,
transaction rollback, and lossless restart reconstruction.

Audit document:

```text
docs/PROJECT_FULL_AUDIT.md
```

Product definition:

```text
docs/PROJECT_VISION.md
```

Development roadmap:

```text
docs/ROADMAP_AFTER_AUDIT.md
```

---

## Verified Product Direction

InvestmentTerminal is a personal investment intelligence platform.

Core flow:

```text
Market / external data
→ deterministic analysis
→ Review Package
→ immutable History
→ Knowledge
→ AI interpretation
→ explainable investment review
```

---

## Current Audit Conclusion

The architecture is suitable for further development.

Main missing product capabilities:

- multi-asset intelligence
- ETF intelligence
- transaction-based portfolio history
- portfolio risk/rebalancing
- macro/news context
- market discovery
- user interface
- broker integrations

Architecture redesign is not required.

---

## Working Protocol

Before every code package:

1. Read current files from GitHub.
2. Perform focused audit only for affected subsystem.
3. Analyze real repository state only.
4. Do not make assumptions.
5. Validate against PROJECT_VISION.md and architecture.
6. Provide complete changed files.
7. Update this checkpoint document.

After implementation:

- git add
- commit
- tests
- CI analysis after user confirmation.

---

## Latest Package

```text
Phase 2 Package 11 — SQLite Valuation History Persistence
```

Files:

```text
investment_terminal/portfolio/portfolio_valuation_history_sqlite_store.py
investment_terminal/portfolio/portfolio_valuation_history_sqlite_repository.py
tests/test_portfolio_valuation_history_sqlite_repository.py
DataModel.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ e8b2f621e07621293e9d8a785459771f7924148e
```

Architecture/product alignment:

- SQLite schema version 1 binds immutable ledger and portfolio metadata;
- canonical strict JSON preserves complete valuation evidence across restart;
- snapshot identities remain append-only and cannot be replaced;
- indexed temporal queries are deterministic and timezone-aware;
- failed appends roll back and corrupt payloads fail visibly;
- canonical Review History remains unchanged.
