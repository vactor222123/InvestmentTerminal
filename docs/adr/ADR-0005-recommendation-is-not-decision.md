
# ADR-0005 — Recommendation Is Not Decision

**Status:** Accepted  
**Date:** 2026-08-02  
**Decision owner:** Investment Terminal Architecture  
**Scope:** Recommendation Domain, Decision Domain, AI Layer, User Experience

---

# Context

Investment Terminal performs deterministic analysis of portfolio data, market
data and financial evidence to produce machine-generated recommendations.

These recommendations assist the investor, but they do not replace human
judgement.

Financial decisions always depend on factors beyond deterministic analysis,
including personal goals, liquidity needs, tax situation, risk tolerance and
external events.

The architecture must clearly separate analytical output from investment
decisions.

---

# Problem

How should Investment Terminal present recommendations without implying that
they are automatic investment decisions or financial advice?

---

# Decision

A **Recommendation** is a deterministic analytical conclusion derived from
available evidence.

A **Decision** is the final action taken by the investor.

The product must always preserve this distinction.

The relationship is:

```text
Evidence
      ↓
Deterministic Analysis
      ↓
Recommendation
      ↓
AI Explanation (optional)
      ↓
Human Decision
```

No component of Investment Terminal may treat a recommendation as an executed
trade or mandatory action.

---

# Decision Details

## Recommendation

A recommendation may express:

- BUY
- ACCUMULATE
- HOLD
- REDUCE
- SELL
- WATCH

It is produced using deterministic rules and available evidence.

## Decision

A decision belongs to the investor.

It may be influenced by:

- recommendation;
- portfolio allocation;
- personal strategy;
- taxation;
- liquidity requirements;
- macroeconomic events;
- individual judgement.

The system supports—but never replaces—the investor.

## AI Responsibilities

The AI layer may:

- explain recommendations;
- compare scenarios;
- highlight risks;
- identify missing evidence;
- discuss trade-offs.

The AI must not claim certainty or imply that a recommendation guarantees an
outcome.

---

# Rationale

Separating recommendations from decisions:

- avoids false authority;
- improves transparency;
- supports explainability;
- reflects real-world investing;
- aligns with the product philosophy.

This distinction also allows historical analysis of:

- recommendations made;
- decisions taken;
- outcomes observed.

---

# Alternatives Considered

## Recommendation Equals Decision

Rejected.

This would imply automated investing and obscure the user's responsibility.

## Automatic Trade Execution

Rejected.

Investment Terminal is an intelligence platform, not an execution platform.

## AI Makes Final Decisions

Rejected.

The architecture intentionally keeps humans responsible for investment actions.

---

# Positive Consequences

- clear product boundaries;
- realistic user expectations;
- easier explanation of recommendations;
- compatibility with historical evaluation;
- supports future Decision Trace functionality.

---

# Negative Consequences

- users must still make final decisions;
- recommendations may differ from user actions;
- additional documentation is required.

These costs are accepted because preserving human agency is a core product
value.

---

# Compliance Rules

A change complies with this ADR when:

- recommendations remain advisory;
- decision ownership remains with the user;
- AI distinguishes facts from interpretation;
- documentation preserves this distinction.

A change violates this ADR when:

- recommendations are presented as guaranteed actions;
- automatic execution is implied;
- the product claims certainty about future outcomes.

---

# Implementation Status

| Area | Status |
|---|---|
| Recommendation engine | Implemented |
| Decision support philosophy | Implemented |
| Decision Trace | Planned (Sprint 12+) |
| Historical recommendation timeline | Planned |
| Decision timeline | Planned |

---

# Related Documents

- PROJECT_VISION.md
- CONSTITUTION.md
- INVESTMENT_PHILOSOPHY.md
- PRODUCT_VALUES.md
- GLOSSARY.md
- QUALITY_ATTRIBUTES.md
- ADR-0001 Review Package Is the Only AI Interface
- ADR-0004 Confidence Measures Evidence Quality

---

# Future Evolution

Future versions may introduce:

- Decision Trace;
- scenario comparison;
- historical recommendation evaluation;
- personal decision journals;
- knowledge-driven decision support.

None of these capabilities change the architectural rule that recommendations
support decisions—they do not replace them.

---

# Guiding Statement

> Recommendations inform.

> Evidence explains.

> The investor decides.
