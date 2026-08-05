# InvestmentTerminal AI Context

## Mission

InvestmentTerminal is a private, local-first investment analysis platform for deterministic analysis, transparent decisions, portfolio review, and preserved historical evidence.

The system should explain:

- what it currently concludes;
- which evidence produced that conclusion;
- what it concluded previously;
- why historical conclusions changed.

## Current architecture

The main analytical flow is:

```text
market and fundamental data
        ↓
technical and fundamental analysis
        ↓
decision
        ↓
ranking
        ↓
recommendation
        ↓
review package
        ↓
immutable archive + append-only manifest
        ↓
verified SQLite historical store
        ↓
timeline and future knowledge systems
```

## Architectural boundaries

### Domain layers

Primary domains include:

- portfolio;
- market and external data;
- technical analysis;
- fundamental analysis;
- decision engine;
- ranking and recommendation;
- review;
- history.

### Composition boundary

CLI modules:

- resolve arguments and paths;
- construct services;
- orchestrate workflows;
- present user-facing errors and output.

CLI modules must not own business rules that belong in domain services or models.

### Review boundary

The Review Domain assembles completed analytical outputs. It must not duplicate or recalculate analytical logic owned by other domains.

### History boundary

The History Domain preserves immutable evidence and builds verified, normalized, rebuildable query representations.

Canonical hierarchy:

```text
immutable archived review package
        ↓
append-only manifest metadata
        ↓
rebuildable SQLite history
        ↓
derived timeline
        ↓
future knowledge
```

## Engineering principles

1. Reliability over cleverness.
2. Correctness before convenience.
3. Deterministic behavior and stable ordering.
4. Explicit contracts over implicit conventions.
5. Preserve evidence before interpretation.
6. Keep public contracts stable.
7. Prefer focused changes over broad rewrites.
8. Reuse proven infrastructure.
9. Refactor only when it reduces future complexity.
10. Tests and documentation are part of implementation.

## Established technical rules

- Persisted/exported timestamps are timezone-aware.
- UTC is the canonical storage timezone.
- Historical archive bytes are immutable.
- Historical archive creation is exclusive.
- Manifest storage is append-only JSON Lines.
- Checksums verify archived evidence.
- SQLite history is not the source of truth.
- Domain models are explicit and commonly frozen/slotted.
- External provider payloads are normalized before entering core analysis.
- Missing data must remain distinguishable from weak data.
- Mutable JSON output uses atomic replacement.
- Shared primitive validation belongs in `investment_terminal.utils.validation`.
- Domain-specific validation remains in the owning domain.

## Shared infrastructure

Current shared helpers include:

```text
investment_terminal/utils/validation.py
investment_terminal/utils/atomic_write.py
```

The utilities package must not become a miscellaneous dumping ground.

## Required reading before major changes

- `docs/README.md`
- `docs/DOMAIN_MAP.md`
- `docs/ARCHITECTURE_REVIEW_SPRINT_12.md`
- `docs/PROJECT_STATUS.md`
- relevant domain documentation
- relevant tests

## Decision policy

Before introducing a new abstraction, confirm that it:

- solves an observed repeated problem;
- reduces duplication or risk;
- respects domain ownership;
- has focused tests;
- is expected to be reused.

Before changing an established contract, document:

- why the change is needed;
- compatibility impact;
- migration path;
- schema-version ownership.

## Prohibited shortcuts

- no silent partial persistence;
- no naive persisted datetimes;
- no hidden missing-data substitution;
- no domain-to-CLI imports;
- no history dependency from analytical domains;
- no overwriting immutable archives;
- no global schema version shared by unrelated domains;
- no mass refactoring without a focused reason and regression coverage.
