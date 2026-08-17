# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint

**Current repository:** `vactor222123/InvestmentTerminal`
**Current branch:** `develop`
**Current GitHub baseline:** `143add3`
**Current local package:** Phase 3 Package 1 — provider-neutral portfolio risk inputs
**Current phase:** Phase 3 — Portfolio Decision Intelligence
**Current next action:** Add deterministic portfolio drawdown analysis

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

Phase 2 Package 12 adds explicit acquisition-lot selection and deterministic
lot-level attribution without imposing an implicit jurisdictional disposal method.

Phase 2 is closed after verifying every roadmap scope item against the current
Portfolio modules and tests at green CI baseline `349620e`. The closure record
is `docs/PHASE_2_CLOSURE.md`.

Phase 3 Package 1 adds provider-neutral, currency-explicit portfolio and
instrument return-series inputs with ordered periods, cutoff validation, and
source provenance, without calculating or classifying risk.

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
Phase 3 Package 1 — Provider-Neutral Portfolio Risk Inputs
```

Files:

```text
investment_terminal/portfolio/portfolio_risk_inputs.py
tests/test_portfolio_risk_inputs.py
DataModel.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 143add3f03f1ef8d76fe3a3abfe2f732732f3782
```

Architecture/product alignment:

- return periods are finite, timezone-aware, unique, ordered, and non-overlapping;
- portfolio and instrument identities remain explicit and deterministic;
- observation currency and provider-neutral provenance are preserved;
- no observation or fetch timestamp may exceed the risk cutoff;
- drawdown, volatility, correlation, classifications, and recommendations remain separate;
- canonical Review History remains unchanged.
