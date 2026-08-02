
# GLOSSARY.md

# Investment Terminal — Glossary

**Status:** Canonical Terminology

This glossary defines the official meaning of important terms used throughout
Investment Terminal. These definitions should be used consistently in code,
documentation, RFCs and ADRs.

---

## Analysis

The deterministic process of transforming validated financial data into
structured signals.

---

## Asset

A financial instrument such as a stock, ETF, bond or cash position.

---

## Canonical Model

The primary data model representing a business concept inside the system.

---

## Confidence

A measure of the quality, completeness and consistency of the available
evidence supporting an analysis.

**Confidence is NOT a prediction of future returns.**

---

## Contribution Plan

A deterministic allocation proposal for newly available capital based on the
current portfolio policy.

---

## Decision

The final investment action chosen by the investor.

Recommendations support decisions but never replace them.

---

## Decision Trace

A structured explanation describing why a recommendation or deployment proposal
was produced.

---

## Deployment

The proposed allocation of available capital into portfolio sleeves or assets.

---

## Domain

A coherent business area with a single responsibility (Portfolio, Review,
History, Knowledge, etc.).

---

## Evidence

Validated information used to support calculations or recommendations.

Evidence may originate from market data, fundamentals, portfolio information or
historical records.

---

## Historical Snapshot

An immutable record describing the complete state of a review at a specific
point in time.

---

## History

The permanent archive of historical snapshots and related metadata.

History is immutable.

---

## Insight

A meaningful interpretation derived from multiple pieces of evidence.

---

## Investment Review Package

The canonical structured output of the Python engine.

It is the primary interface between deterministic analysis and AI-assisted
interpretation.

---

## Knowledge

Verified patterns or conclusions derived from accumulated historical evidence.

---

## Market Value

The calculated value of the current portfolio using available market prices or
documented fallback rules.

---

## Policy Gap

The difference between current allocation and target allocation defined by the
portfolio policy.

---

## Portfolio

The complete collection of holdings, cash, policy and related configuration.

---

## Recommendation

A machine-generated assessment derived from deterministic analysis.

A recommendation is not investment advice.

---

## Review

A complete analysis of the portfolio and supporting evidence for a specific
execution.

---

## Schema Version

The version identifier of a serialized format used to maintain compatibility.

---

## Signal

A structured output produced by deterministic analysis (for example, technical
or fundamental signals).

Signals are inputs to recommendations.

---

## Snapshot

A stored representation of a review or portfolio state.

---

## Source of Truth

The canonical location from which a specific type of information is considered
authoritative.

---

## Traceability

The ability to identify the origin of any derived value.

---

## Validation

The process of confirming that data satisfies the required business rules before
it is used.

---

# Terminology Rules

- Use terms consistently.
- Avoid introducing synonyms for canonical concepts.
- Prefer glossary terms in documentation and code comments.
- Update this document whenever a new core concept is introduced.

---

# Guiding Statement

Shared terminology is part of the architecture.

Consistent language reduces ambiguity and improves long-term maintainability.
