# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint

**Current repository:** `vactor222123/InvestmentTerminal`
**Current branch:** `develop`
**Current GitHub baseline:** `400878a`
**Current local package:** Phase 1 Package 4 — ETF evidence and characteristics
**Current phase:** Phase 1 — Multi-Asset Evidence Foundation
**Current next action:** Define ETF holdings and exposure composition contracts

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
Phase 1 Package 4 — ETF Evidence and Characteristics
```

Files:

```text
investment_terminal/market/etf_evidence_models.py
tests/test_etf_evidence_models.py
DataModel.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 400878a3be9068b3c1a6f2a1e2508b99a6040a2c
```

Architecture/product alignment:

- ETF characteristics are linked to the canonical ETF instrument identity;
- unavailable characteristics remain `None` and are listed explicitly;
- expense ratio, AUM, currency, and holdings count have deterministic bounds;
- source provenance and quality remain separate, reusable evidence contracts;
- provider clients, persistence, Review, and portfolio JSON remain unchanged.
