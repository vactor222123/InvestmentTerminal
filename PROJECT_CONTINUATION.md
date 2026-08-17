# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint

**Current repository:** `vactor222123/InvestmentTerminal`
**Current branch:** `develop`
**Current GitHub baseline:** `5318963`
**Current local package:** Phase 2 Package 7 — realised performance calculation
**Current phase:** Phase 2 — Portfolio Lifecycle Intelligence
**Current next action:** Add unrealised performance projection using explicit current prices

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
Phase 2 Package 7 — Realised Performance Calculation
```

Files:

```text
investment_terminal/portfolio/realized_performance.py
tests/test_realized_performance.py
DataModel.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 531896325a3af9bbfe4577712d26f9d244d2ef3e
```

Architecture/product alignment:

- realised results retain exact SELL transaction and instrument provenance;
- allocated cost basis follows deterministic average-cost accounting;
- sale-level gain/loss and return percentage remain explicit;
- summaries never aggregate unlike currencies;
- dividends, fees, unrealised valuation, persistence, and snapshots remain unchanged.
