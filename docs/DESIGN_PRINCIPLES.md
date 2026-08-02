
# DESIGN_PRINCIPLES.md

# Investment Terminal — Design Principles

**Status:** Canonical Product Design Principles

---

# 1. Purpose

This document defines the architectural and software design principles used when designing new capabilities for Investment Terminal.

Architecture defines *where* responsibilities belong.

Development Guidelines define *how* we implement them.

Design Principles define *how we think* before writing code.

---

# 2. Core Philosophy

Good architecture minimizes future complexity.

Every design decision should improve:

- clarity;
- maintainability;
- traceability;
- correctness;
- long-term evolution.

---

# 3. Design Priorities

Priority order:

1. Correctness
2. Determinism
3. Explainability
4. Simplicity
5. Extensibility
6. Performance

Performance must never sacrifice correctness.

---

# 4. Single Responsibility

Every class, service and module should have one primary reason to change.

Examples:

- PortfolioSnapshotBuilder builds snapshots.
- ContributionPlanner allocates capital.
- ReviewAssembler assembles review packages.

Avoid "god objects".

---

# 5. Domain-Driven Design

Business logic belongs inside domains.

Domains communicate through explicit models instead of hidden shared state.

---

# 6. Explicit Dependencies

Dependencies should be injected, not created internally.

Prefer constructors over global singletons.

---

# 7. Canonical Models

Business concepts require canonical models.

Avoid passing anonymous dictionaries through multiple layers.

Use adapters only for serialization or integration.

---

# 8. Immutability

Prefer immutable value objects.

Financial calculations should not mutate previous state.

Historical data must always remain immutable.

---

# 9. Deterministic Calculations

Identical inputs must produce identical outputs.

Avoid:

- random ordering;
- hidden timestamps;
- implicit external state.

---

# 10. Explicit State

Represent important states explicitly.

Examples:

READY

PARTIAL

STALE

MISSING

INVALID

Never overload None with multiple meanings.

---

# 11. Separation of Concerns

Keep separate:

- acquisition;
- validation;
- calculation;
- orchestration;
- serialization;
- presentation.

---

# 12. Composition over Duplication

Extract reusable components rather than copying business logic.

Duplicate rules become inconsistent over time.

---

# 13. Stable Contracts

Public interfaces should evolve carefully.

Breaking changes require:

- documentation;
- versioning;
- migration strategy where appropriate.

---

# 14. Data First

Facts precede interpretation.

Pipeline:

Raw Data
→ Validation
→ Models
→ Calculations
→ Signals
→ Decisions
→ Human Interpretation

---

# 15. Error Visibility

Failures must be visible.

Fallback behavior should always indicate:

- why;
- what changed;
- what was unavailable.

---

# 16. History by Design

Every important product artifact should be designed with historical storage in mind.

Future comparison should not require redesign.

---

# 17. AI Boundary

Python is responsible for:

- deterministic calculations;
- structured outputs.

AI is responsible for:

- explanation;
- synthesis;
- scenarios.

Keep this boundary stable.

---

# 18. Testability

Design code that can be tested without:

- network;
- filesystem (unless required);
- real market APIs.

Prefer dependency inversion.

---

# 19. Evolvability

New domains should integrate without rewriting existing domains.

Extension is preferred over modification.

---

# 20. Documentation by Design

Architecture, data models and public contracts evolve together.

Documentation is updated in the same engineering cycle.

---

# 21. Anti-Patterns

Avoid:

- business logic inside CLI;
- circular dependencies;
- hidden mutable globals;
- duplicated calculations;
- silent fallback;
- undocumented formats;
- magic constants.

---

# 22. Design Review Questions

Before implementation ask:

- Does this belong in the correct domain?
- Is an existing model reusable?
- Can it be explained simply?
- Can it be tested independently?
- Can it be archived?
- Does it preserve history?
- Does it improve long-term maintainability?

---

# 23. Long-Term Principles

> Design for understanding before optimization.

> Prefer explicit architecture over accidental structure.

> Stable data contracts outlive implementations.

> Preserve evidence.

> Keep domain boundaries clean.

> Make future refactoring easier, not harder.

> Every new capability should reduce uncertainty, not increase complexity.
