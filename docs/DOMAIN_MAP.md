
# DOMAIN_MAP.md

# Investment Terminal — Domain Map

**Status:** Canonical Architecture Map

---

# 1. Purpose

This document defines the business domains of Investment Terminal, their
responsibilities, boundaries, dependencies and evolution rules.

The goal is to keep architecture understandable as the product grows.

---

# 2. High-Level Domain Map

```
Investment Terminal

├── Market
├── Technical Analysis
├── Fundamental Analysis
├── Recommendation
├── Portfolio
├── Review
├── History (planned)
├── Knowledge (planned)
├── Decision (planned)
└── Infrastructure
```

---

# 3. Domain Overview

| Domain | Primary Responsibility |
|---------|------------------------|
| Market | Market data and quotes |
| Technical | Technical indicators and signals |
| Fundamental | Company fundamentals |
| Recommendation | Deterministic recommendations |
| Portfolio | Holdings, allocation and policy |
| Review | Assemble the review package |
| History | Immutable snapshot archive |
| Knowledge | Learn from historical evidence |
| Decision | Combine evidence into decision support |
| Infrastructure | CLI, storage, logging and configuration |

---

# 4. Portfolio Domain

Purpose:
Manage portfolio state.

Owns:

- holdings
- policy
- market value
- allocation
- contribution planning

Inputs:

- portfolio configuration
- market quotes

Outputs:

- portfolio snapshot
- policy gap
- contribution plan

Must NOT:

- download market data
- perform technical analysis

---

# 5. Market Domain

Purpose:

Provide validated market prices.

Owns:

- quote providers
- exchange metadata
- completed candles

Must NOT:

- know portfolio allocation
- generate recommendations

---

# 6. Technical Analysis Domain

Purpose:

Transform price history into deterministic technical signals.

Examples:

- RSI
- EMA
- SMA
- MACD
- ATR

Consumes market data only.

---

# 7. Fundamental Analysis Domain

Purpose:

Evaluate financial quality of companies.

Produces structured fundamental signals.

Does not generate final recommendations.

---

# 8. Recommendation Domain

Purpose:

Combine deterministic evidence into recommendations.

Consumes:

- technical signals
- fundamental signals

Produces:

- recommendation
- rationale
- confidence inputs

---

# 9. Review Domain

Purpose:

Assemble the canonical investment_review_package.json.

Consumes outputs from other domains.

Performs orchestration only.

No business calculations belong here.

---

# 10. History Domain (Planned)

Purpose:

Preserve immutable historical reviews.

Future responsibilities:

- snapshot archive
- manifest
- timeline
- snapshot diff

History never modifies archived records.

---

# 11. Knowledge Domain (Planned)

Purpose:

Extract reusable knowledge from historical evidence.

Consumes history.

Produces:

- patterns
- historical insights
- calibrated knowledge

Never rewrites history.

---

# 12. Decision Domain (Planned)

Purpose:

Support investment decisions.

Combines:

- recommendations
- portfolio context
- history
- confidence
- knowledge

Produces decision support only.

The investor remains responsible for final actions.

---

# 13. Infrastructure Domain

Responsibilities:

- CLI
- serialization
- filesystem
- SQLite
- logging
- configuration

Infrastructure must remain independent of business rules.

---

# 14. Allowed Dependencies

```
Market
      ↓
Technical
      ↓
Recommendation

Fundamental
      ↓
Recommendation

Portfolio
      ↓
Review

Recommendation
      ↓
Review

Review
      ↓
History
      ↓
Knowledge
      ↓
Decision
```

---

# 15. Forbidden Dependencies

History → Market API

History → Technical Analysis

Portfolio → Yahoo

Review → Indicator Calculations

Knowledge → Snapshot Modification

Decision → Portfolio Mutation

Infrastructure → Business Rules

---

# 16. Data Flow

```
External Data
      ↓
Validation
      ↓
Canonical Models
      ↓
Analysis
      ↓
Recommendations
      ↓
Portfolio
      ↓
Review Package
      ↓
History
      ↓
Knowledge
      ↓
AI Interpretation
      ↓
Human Decision
```

---

# 17. Domain Maturity

Current assessment:

| Domain | Status |
|---------|--------|
| Portfolio | Mature |
| Review | Mature |
| Recommendation | Mature |
| Market | Mature |
| Technical | Mature |
| Fundamental | Mature |
| History | Planned |
| Knowledge | Planned |
| Decision | Planned |

---

# 18. Evolution Rules

New capabilities should extend existing domains whenever possible.

Create a new domain only when a distinct business responsibility emerges.

---

# 19. Architecture Review Questions

Before introducing a change:

- Does it belong to the correct domain?
- Does it violate domain boundaries?
- Does it duplicate another capability?
- Can it be tested independently?
- Does it preserve historical integrity?

---

# 20. Guiding Statements

> Domains own business capabilities.

> Models represent business concepts.

> Services implement behaviour.

> Review assembles information.

> History preserves evidence.

> Knowledge learns from history.

> Decision support assists the investor.

> Architecture should become simpler as the product evolves.
