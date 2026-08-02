
# ADR-0004 — Confidence Measures Evidence Quality

**Status:** Accepted  
**Date:** 2026-08-02  
**Decision owner:** Investment Terminal Architecture  
**Scope:** Recommendation Domain, Review Domain, History Domain, AI Layer

---

# Context

Investment Terminal produces deterministic analysis from validated financial
data. Users naturally ask how confident the system is in its conclusions.

Many investment products use "confidence" to imply the probability that a
recommendation will be profitable. This interpretation is misleading because
future market outcomes cannot be known deterministically.

Investment Terminal requires a definition of confidence that is objective,
repeatable and measurable.

---

# Problem

How should the product communicate confidence without implying prediction of
future returns?

---

# Decision

Confidence represents the **quality of the available evidence**, not the
probability that a recommendation will succeed.

Confidence answers:

- How complete is the evidence?
- How fresh is the data?
- How consistent are the signals?
- How much deterministic support exists?

Confidence does **not** answer:

- Will the asset outperform?
- What is the probability of profit?
- Will the market rise tomorrow?

---

# Decision Details

Future confidence calculations may include components such as:

- data completeness;
- data freshness;
- source reliability;
- signal agreement;
- portfolio coverage;
- historical availability;
- validation success.

Confidence should decrease when:

- important data is missing;
- evidence is stale;
- sources conflict;
- calculations fall back to defaults.

Confidence should increase when:

- evidence is complete;
- data is current;
- signals are internally consistent;
- validation succeeds.

---

# Rationale

This definition:

- avoids false precision;
- separates facts from forecasts;
- encourages transparency;
- allows deterministic scoring;
- supports future historical calibration.

Confidence therefore becomes an engineering quality metric rather than a market
prediction.

---

# Alternatives Considered

## Confidence as Probability

Rejected.

Future returns cannot be measured deterministically.

## Binary Confidence (High/Low)

Rejected.

Too little information for meaningful interpretation.

## No Confidence Metric

Rejected.

Users benefit from understanding the quality of the underlying evidence.

---

# Positive Consequences

- greater transparency;
- better user expectations;
- explicit handling of incomplete data;
- improved AI explanations;
- historical calibration becomes possible.

---

# Negative Consequences

- users may initially misunderstand the metric;
- documentation and UI must explain the meaning clearly;
- confidence model requires continued refinement.

These costs are accepted because clarity is more valuable than ambiguous
certainty.

---

# Compliance Rules

A change complies with this ADR if:

- confidence measures evidence quality;
- missing data reduces confidence;
- confidence never represents expected return probability;
- calculations remain deterministic.

A change violates this ADR if:

- confidence is presented as forecast accuracy;
- confidence is based on subjective intuition;
- confidence hides missing evidence.

---

# Implementation Status

| Area | Status |
|---|---|
| Initial confidence concept | Defined |
| Confidence section in Review Package | Planned |
| Component-based confidence model | Planned (Sprint 12+) |
| Historical calibration | Planned |
| Confidence timeline | Planned |

---

# Related Documents

- PROJECT_VISION.md
- INVESTMENT_PHILOSOPHY.md
- DATA_MODEL.md
- QUALITY_ATTRIBUTES.md
- GLOSSARY.md
- ADR-0001 Review Package Is the Only AI Interface

---

# Future Evolution

Future versions may expose confidence sub-scores for:

- freshness;
- completeness;
- consistency;
- validation;
- historical support.

The overall principle remains unchanged:

Confidence measures evidence quality—not future certainty.

---

# Guiding Statement

> Confidence should tell the user how much they can trust the available
> evidence, never how certain the future is.
