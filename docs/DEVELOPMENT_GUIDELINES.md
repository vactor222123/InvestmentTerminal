
# DEVELOPMENT_GUIDELINES.md

# Investment Terminal — Development Guidelines

**Status:** Canonical Engineering Standard  
**Applies to:** Entire repository

---

# 1. Purpose

This document defines the engineering rules for developing Investment Terminal.

The objective is to ensure the product remains:

- understandable;
- deterministic;
- testable;
- maintainable;
- reproducible;
- extensible for many years.

These guidelines complement:

- PROJECT_VISION.md
- CONSTITUTION.md
- ARCHITECTURE.md
- DATA_MODEL.md

When conflicts exist, the Constitution takes precedence.

---

# 2. Engineering Principles

1. Readability over cleverness.
2. Determinism over hidden behavior.
3. Explicit models over anonymous dictionaries.
4. Small focused services.
5. One responsibility per module.
6. Documentation evolves with architecture.
7. Preserve backward compatibility where practical.
8. Every bug fix requires a regression test.
9. Missing data must be explicit.
10. Build for the next decade, not the next release.

---

# 3. Repository Organization

Business logic belongs to domains.

Example layout:

```
investment_terminal/
    portfolio/
    market/
    recommendation/
    review/
    history/
    knowledge/
    decision/
    infrastructure/
```

Avoid generic folders such as:

- misc
- random
- temp
- helpers (for business logic)

Utilities may exist only for truly generic reusable code.

---

# 4. Domain Rules

Each domain owns its models and services.

Examples:

Portfolio:
- owns holdings
- owns policy
- owns allocation
- must not download market data

Review:
- assembles outputs
- must not calculate RSI

History:
- archives data
- must not modify archived snapshots

Knowledge:
- derives insights
- must never rewrite history

---

# 5. Coding Standards

Prefer:

- descriptive names;
- pure functions where possible;
- immutable dataclasses;
- explicit dependency injection;
- early validation.

Avoid:

- hidden globals;
- implicit state;
- magic numbers;
- duplicated business rules.

---

# 6. Data Models

Canonical models should:

- validate in constructors;
- reject invalid state;
- serialize predictably;
- expose derived values explicitly.

Do not replace structured models with loosely typed dictionaries.

---

# 7. Service Design

Services should:

- perform one business task;
- remain stateless;
- receive dependencies through constructors;
- avoid filesystem access unless that is their responsibility.

---

# 8. Error Handling

Errors should be:

- explicit;
- actionable;
- deterministic.

Never silently ignore invalid financial data.

Fallbacks must be visible.

---

# 9. Logging

Log meaningful events:

- import completed;
- snapshot archived;
- quotes missing;
- review generated.

Never log secrets or private credentials.

---

# 10. Configuration

Configuration belongs in configuration objects or files.

Business rules must never depend on hard-coded paths scattered through the codebase.

---

# 11. Serialization

Long-lived JSON artifacts require:

- schema_version
- deterministic ordering where practical
- ISO-8601 timestamps
- explicit status fields

---

# 12. Testing Standards

Every feature requires tests.

Required categories:

- unit tests
- regression tests
- serialization tests
- compatibility tests

Tests must not depend on:

- internet connectivity;
- live APIs;
- current market prices.

---

# 13. Documentation Rules

Update documentation whenever changing:

- architecture;
- public CLI;
- JSON schema;
- canonical models;
- review package structure.

Documentation is part of the product.

---

# 14. Git Workflow

Recommended workflow:

1. Implement one logical change.
2. Run formatting/tools if applicable.
3. Run test suite.
4. Review changes.
5. Commit with a clear message.
6. Push only passing work.

Commit messages should describe intent rather than implementation details.

---

# 15. RFC and ADR

Create an RFC before:

- introducing a new domain;
- creating a new persistent format;
- major product capabilities.

Create an ADR when:

- architectural direction changes;
- source of truth changes;
- long-term engineering decisions are made.

---

# 16. Architecture Review Checklist

Before merging:

- Does the change belong to the correct domain?
- Does it duplicate existing logic?
- Are models still canonical?
- Are tests sufficient?
- Is documentation updated?
- Is backward compatibility preserved?

---

# 17. Quality Gates

Changes should satisfy:

- passing tests;
- deterministic behavior;
- documented public interfaces;
- reproducible outputs;
- no hidden breaking changes.

---

# 18. Backward Compatibility

Prefer compatibility over unnecessary breaking changes.

When breaking changes are unavoidable:

- document them;
- version schemas;
- provide migration where appropriate.

---

# 19. Performance

Correctness has priority over micro-optimizations.

Optimize only after measurement.

---

# 20. Security & Privacy

Never expose:

- credentials;
- tokens;
- private portfolio information unnecessarily.

Sensitive information must remain local unless intentionally exported.

---

# 21. Refactoring

Refactoring should:

- reduce complexity;
- improve readability;
- preserve behavior.

Behavioral changes require tests.

---

# 22. Technical Debt

Record intentional technical debt.

Avoid accumulating undocumented shortcuts.

---

# 23. Long-Term Evolution

Every major capability should evolve through:

Problem
→ RFC
→ Architecture
→ Data Model
→ Implementation
→ Tests
→ Documentation
→ Review

---

# 24. Engineering Checklist

Before finishing work:

- [ ] Tests pass
- [ ] Documentation updated
- [ ] No duplicated logic
- [ ] Domain boundaries respected
- [ ] Public contracts preserved
- [ ] Review Package compatibility verified
- [ ] History compatibility considered
- [ ] Git status clean

---

# 25. Guiding Statements

> Build systems that remain understandable.

> Preserve history.

> Prefer explicit uncertainty over false certainty.

> Stable interfaces create long-term value.

> Every completed sprint should leave the product cleaner than before.
