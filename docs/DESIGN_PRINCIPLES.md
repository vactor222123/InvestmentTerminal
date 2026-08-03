# DESIGN_PRINCIPLES.md

# Investment Terminal — Design Principles

**Status:** Canonical Product Design Principles  
**Updated after:** Sprint 12 — Historical Intelligence Foundation

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
- historical integrity;
- long-term evolution.

Investment Terminal is designed as a long-lived product. A locally convenient shortcut is not acceptable when it creates hidden coupling, destroys evidence, or makes future evolution harder.

---

# 3. Design Priorities

Priority order:

1. Correctness
2. Determinism
3. Integrity
4. Explainability
5. Simplicity
6. Extensibility
7. Performance

Performance must never sacrifice correctness or historical integrity.

---

# 4. Single Responsibility

Every class, service, and module should have one primary reason to change.

Examples:

- `PortfolioSnapshotBuilder` builds snapshots.
- `ContributionPlanner` allocates capital.
- `ReviewAssembler` assembles review packages.
- `HistoricalSnapshotArchive` preserves immutable package bytes.
- `HistoricalSnapshotManifest` indexes archived snapshots.
- `HistoricalReviewPackageLoader` verifies archived evidence.
- `HistoricalTimelineBuilder` derives timeline events.

Avoid "god objects" and large orchestration files that absorb domain logic.

---

# 5. Domain-Driven Design

Business logic belongs inside domains.

Domains communicate through explicit models instead of hidden shared state.

Current first-class domains include:

- Portfolio;
- Market Data;
- Review;
- History.

The History Domain owns:

- historical snapshot identity;
- archive integrity;
- manifest indexing;
- structured history import;
- timeline generation.

Future Knowledge capabilities must build on History rather than bypass it.

---

# 6. Explicit Dependencies

Dependencies should be injected, not created through hidden global state.

Prefer constructors over global singletons.

Application services and pipelines may compose domain components, but dependencies must remain visible at construction time.

A CLI should configure dependencies, not become the place where business rules live.

---

# 7. Canonical Models

Business concepts require canonical models.

Avoid passing anonymous dictionaries through multiple layers when the data represents a stable domain concept.

Use adapters and raw dictionaries only at boundaries such as:

- JSON serialization;
- external integration;
- compatibility layers;
- archived package loading.

Once data enters a domain, normalize it into explicit models or validated structured records.

---

# 8. Immutability

Prefer immutable value objects.

Financial calculations should not mutate previous state.

Historical data must always remain immutable.

For historical evidence:

- archived Review Package bytes are never rewritten;
- snapshot identity is permanent;
- archive paths are unique;
- manifest records are append-only;
- completed timeline events are not silently regenerated;
- previous recommendations and deployment decisions are never overwritten.

Corrections must create new evidence and may explicitly supersede earlier evidence.

---

# 9. Deterministic Calculations

Identical inputs must produce identical outputs.

Avoid:

- random ordering;
- hidden timestamps;
- implicit external state;
- nondeterministic serialization;
- unstable generated identifiers where stable keys are available.

Historical imports and timeline generation must use deterministic ordering so that repeated reconstruction produces equivalent structured history.

---

# 10. Explicit State

Represent important states explicitly.

Examples:

```text
READY
PARTIAL
STALE
MISSING
INVALID
ARCHIVED
VERIFIED
CONNECTED
NOT_CONNECTED
COST_BASIS_ONLY
MARKET_VALUE_CONNECTED
```

Never overload `None` with multiple meanings.

Absence of data, failed validation, disconnected data, and zero values are different states and must remain distinguishable.

---

# 11. Separation of Concerns

Keep separate:

- acquisition;
- validation;
- calculation;
- orchestration;
- serialization;
- archival;
- indexing;
- normalized storage;
- timeline derivation;
- presentation.

Historical architecture must preserve the distinction between:

```text
Archived JSON
    canonical historical evidence

Manifest
    append-only archive index

SQLite
    normalized query and analytics representation
```

These representations serve different purposes and must not be collapsed into one storage responsibility.

---

# 12. Composition over Duplication

Extract reusable components rather than copying business logic.

Duplicate rules become inconsistent over time.

Pipelines should compose focused services:

```text
Loader
→ Importers
→ Timeline Builder
```

They should not reimplement validation, persistence, or normalization rules already owned by those components.

---

# 13. Stable Contracts

Public interfaces should evolve carefully.

Breaking changes require:

- documentation;
- versioning;
- compatibility analysis;
- migration strategy where appropriate.

Historical package schemas and SQLite schemas must be versioned independently.

Archived evidence must remain readable even after current domain models evolve.

---

# 14. Data First

Facts precede interpretation.

Core analytical pipeline:

```text
Raw Data
→ Validation
→ Models
→ Calculations
→ Signals
→ Decisions
→ Human Interpretation
```

Historical pipeline:

```text
Completed Review Package
→ Immutable Archive
→ Integrity Verification
→ Structured Import
→ Timeline
→ Future Knowledge
```

Knowledge must be derived from preserved evidence, not from undocumented memory.

---

# 15. Error Visibility

Failures must be visible.

Fallback behavior should always indicate:

- why;
- what changed;
- what was unavailable;
- whether evidence was preserved;
- whether structured import completed.

A partially completed historical workflow must not appear successful.

When a multi-stage import fails, either use one database transaction or perform explicit compensating cleanup.

---

# 16. History by Design

Every important product artifact should be designed with historical storage in mind.

Future comparison should not require redesign.

Any new output intended to influence investment decisions should answer:

- Can it be archived?
- Can it be identified?
- Can its integrity be verified?
- Can it be imported into structured history?
- Can it be compared with earlier versions?
- Can its origin and timestamp be reconstructed?

History is not an optional export feature. It is a product capability.

---

# 17. Evidence Is the Source of Truth

Historical evidence and derived indexes must not be confused.

The canonical hierarchy is:

```text
Immutable archived artifact
        ↓
Append-only metadata index
        ↓
Rebuildable structured database
        ↓
Derived timeline and knowledge
```

Derived data may be rebuilt.

Canonical evidence must be preserved.

SQLite must never become the only copy of historical investment evidence.

---

# 18. Verify Before Deriving

No historical artifact may be used for structured import, replay, comparison, or knowledge extraction before integrity verification.

Verification should include, where applicable:

- path safety;
- file existence;
- checksum match;
- encoding validity;
- schema compatibility;
- timestamp identity;
- domain invariants.

A valid JSON file is not automatically trusted evidence.

---

# 19. Rebuildable Projections

Indexes, normalized tables, timelines, and future knowledge projections should be rebuildable from canonical evidence.

This principle enables:

- schema migrations;
- corruption recovery;
- alternative analytical projections;
- compatibility testing;
- reproducible history.

A rebuildable projection must not introduce facts absent from the archived source.

---

# 20. Preserve Original Payloads

Normalization must not silently discard source detail.

Where structured tables store selected fields, preserve the original source object when practical, for example in `payload_json`.

This is especially important for:

- recommendations;
- allocation decisions;
- deployment plans;
- future confidence evidence;
- decision traces.

Normalized columns support queries. Original payloads preserve evidence.

---

# 21. Idempotent Workflows

Synchronization and import workflows should be safe to repeat.

Repeated execution should:

- skip already imported metadata;
- avoid duplicate detail rows;
- avoid duplicate timeline events;
- return a clear result;
- never rewrite historical evidence.

Idempotence must be explicit and tested, not assumed.

---

# 22. Atomicity and Compensation

Multi-stage workflows must not leave misleading partial state.

Preferred order:

1. use a single transaction when boundaries allow it;
2. otherwise use explicit compensating cleanup;
3. preserve canonical snapshot metadata when the immutable archive remains valid;
4. expose failure clearly.

Rollback rules must be documented and tested.

---

# 23. Time Is Domain Data

Historical timestamps are part of the evidence contract.

Requirements:

- important timestamps must be timezone-aware;
- comparisons must use explicit time semantics;
- persisted timestamps should use ISO 8601;
- timeline ordering must be deterministic;
- UTC normalization should be used for cross-system ordering where appropriate.

Generated time, archived time, imported time, and event time are different concepts and must not be conflated.

---

# 24. AI Boundary

Python is responsible for:

- deterministic calculations;
- validation;
- persistence;
- integrity checks;
- structured outputs;
- historical reconstruction.

AI is responsible for:

- explanation;
- synthesis;
- scenario generation;
- narrative interpretation.

AI must not silently alter canonical historical evidence.

Future AI or Knowledge features must cite or reference the evidence from which conclusions were derived.

---

# 25. Testability

Design code that can be tested without:

- network;
- real market APIs;
- uncontrolled clocks;
- uncontrolled UUID generation;
- production filesystem state.

Prefer:

- dependency inversion;
- temporary files and databases;
- injected clocks;
- injected identifier factories;
- deterministic fixtures.

Filesystem and SQLite behavior should be tested directly when they are part of the product contract.

---

# 26. Evolvability

New domains should integrate without rewriting existing domains.

Extension is preferred over modification.

A new historical importer should normally be added as a focused component and composed into the import pipeline.

A new consumer of history should query the History Domain rather than directly coupling itself to archive file layout.

---

# 27. CLI as an Application Boundary

CLI modules should:

- parse arguments;
- configure dependencies;
- invoke application services;
- format results;
- map known failures to user-visible errors.

CLI modules should not:

- contain domain calculations;
- implement persistence rules;
- duplicate validation logic;
- become orchestration monoliths.

When orchestration grows, create an application service or pipeline.

---

# 28. Documentation by Design

Architecture, data models, schemas, workflows, and public contracts evolve together.

Documentation is updated in the same engineering cycle.

Changes to historical storage should trigger review of:

- `ARCHITECTURE.md`;
- `DATA_MODEL.md`;
- `DOMAIN_MAP.md`;
- `QUALITY_ATTRIBUTES.md`;
- `README.md`;
- relevant ADRs;
- sprint review documents.

---

# 29. Anti-Patterns

Avoid:

- business logic inside CLI;
- circular dependencies;
- hidden mutable globals;
- duplicated calculations;
- silent fallback;
- undocumented formats;
- magic constants;
- mutable historical records;
- treating SQLite as canonical evidence;
- importing unverified archives;
- destructive manifest updates;
- deriving facts not present in source evidence;
- partial workflows reported as complete;
- direct coupling to archive folder layout outside the History Domain.

---

# 30. Design Review Questions

Before implementation ask:

- Does this belong in the correct domain?
- Is an existing model reusable?
- Can it be explained simply?
- Can it be tested independently?
- Can it be archived?
- Does it preserve original evidence?
- Is its integrity verifiable?
- Is the derived state rebuildable?
- Is the workflow idempotent?
- Are rollback semantics explicit?
- Are timestamps timezone-aware?
- Does it keep CLI and domain responsibilities separate?
- Does it improve long-term maintainability?

For History-related work also ask:

- What is the canonical Source of Truth?
- What may be rebuilt?
- What must never be overwritten?
- How will schema evolution work?
- Can future comparison use this without redesign?

---

# 31. Long-Term Principles

> Design for understanding before optimization.

> Prefer explicit architecture over accidental structure.

> Stable data contracts outlive implementations.

> Preserve evidence before deriving knowledge.

> Immutable history is more valuable than convenient mutation.

> Derived data should be rebuildable.

> Verification precedes interpretation.

> Keep domain boundaries clean.

> Make future refactoring easier, not harder.

> Every new capability should reduce uncertainty, not increase complexity.

> Investment Terminal should be able to explain not only what it believes now, but what it believed before and why.
