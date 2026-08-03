# QUALITY_ATTRIBUTES.md

# Investment Terminal — Quality Attributes

**Status:** Canonical Quality Standard  
**Updated after:** Sprint 12 — Historical Intelligence Foundation

---

# 1. Purpose

This document defines the quality attributes that guide every architectural,
engineering, and product decision within Investment Terminal.

Features are important.

Quality attributes determine whether those features remain trustworthy,
maintainable, reproducible, and valuable over many years.

When trade-offs are necessary, these attributes provide the decision framework.

---

# 2. Quality Philosophy

Investment Terminal is designed to:

- reduce uncertainty;
- preserve evidence;
- remain deterministic;
- explain conclusions;
- accumulate historical knowledge;
- remain rebuildable from canonical data;
- evolve without losing prior meaning.

A feature that weakens these goals should be reconsidered.

---

# 3. Reliability

The system must produce dependable results.

Requirements:

- validated inputs;
- explicit failures;
- visible fallbacks;
- deterministic calculations;
- no silent corruption;
- no silent partial success;
- repeatable import behavior;
- protected historical evidence.

For multi-stage workflows, success means every required stage completed or the
system clearly reports failure and removes misleading partial state.

---

# 4. Determinism

Identical validated inputs must produce identical outputs.

Avoid:

- hidden randomness;
- implicit global state;
- dependence on execution order;
- unstable serialization;
- nondeterministic timeline ordering;
- hidden current-time dependencies.

Historical imports, event generation, and rebuild operations must be
deterministic.

---

# 5. Integrity

Integrity is a first-class quality attribute.

The system must protect both current analytical data and historical evidence.

Requirements include:

- domain validation;
- foreign-key enforcement;
- duplicate protection;
- checksum verification;
- path safety;
- schema identity checks;
- timestamp identity checks;
- atomic writes or compensating rollback.

A syntactically valid file is not automatically trusted data.

---

# 6. Explainability

Every important output should be explainable.

Recommendations should reference evidence.

Portfolio decisions should reference calculations.

Historical conclusions should reference archived snapshots.

Future Knowledge Domain conclusions should be traceable to:

```text
Knowledge statement
→ Timeline event
→ Structured historical record
→ Archived Review Package
```

---

# 7. Traceability

Every derived value should have a traceable origin.

Examples:

```text
Portfolio Value
→ Quote
→ Instrument
→ Data Source
```

```text
Recommendation
→ Technical Signals
→ Fundamental Signals
→ Ranking Rules
```

```text
Historical Timeline Event
→ Normalized SQLite Record
→ Historical Snapshot
→ Archived Review Package
```

Traceability must survive schema changes and implementation refactoring.

---

# 8. Historical Integrity

History is immutable.

Requirements:

- archived snapshots are never overwritten;
- corrections create new snapshots;
- supersession is explicit;
- timestamps remain preserved;
- checksums identify archived content;
- archive paths remain unique;
- manifest entries remain append-only;
- imported history never rewrites prior evidence;
- timeline events are not silently duplicated.

The archived Review Package is the canonical historical evidence.

---

# 9. Rebuildability

Derived historical structures should be rebuildable from canonical evidence.

Rebuildable components include:

- SQLite snapshot metadata;
- normalized portfolio history;
- normalized holdings;
- normalized recommendations;
- deployment history;
- timeline events;
- future knowledge projections.

This attribute supports:

- recovery from database corruption;
- schema migrations;
- alternative projections;
- reproducible analysis;
- long-term compatibility.

A rebuild must not invent facts absent from the archived source.

---

# 10. Testability

Business logic should be independently testable.

Preferred characteristics:

- dependency injection;
- deterministic fixtures;
- isolated services;
- no mandatory internet access;
- temporary filesystem usage;
- temporary SQLite databases;
- explicit clocks and identifiers where needed.

Filesystem, checksum, archive, and database behavior must be tested directly
when they are part of the product contract.

---

# 11. Maintainability

The codebase should remain understandable years later.

Indicators:

- small focused modules;
- explicit naming;
- minimal duplication;
- documented architecture;
- visible dependency boundaries;
- isolated orchestration;
- localized schema adapters.

History importers should remain separate by responsibility rather than growing
into one large importer.

---

# 12. Modularity

Each domain owns its responsibility.

Examples:

- Portfolio does not download quotes.
- History does not calculate technical indicators.
- Review assembles information rather than performing analysis.
- CLI configures workflows rather than owning business rules.
- Knowledge must consume History rather than bypass it.

The History Domain owns archive, integrity, structured historical storage, and
timeline generation.

---

# 13. Evolvability

The architecture should allow new capabilities without major redesign.

Future additions should extend existing contracts rather than replace them.

Expected extensions include:

- timeline query services;
- snapshot comparison;
- historical replay;
- confidence history;
- evidence relationships;
- Knowledge Domain projections.

New historical capabilities should build on canonical snapshots and structured
history rather than introduce parallel sources of truth.

---

# 14. Backward Compatibility

Long-lived artifacts require compatibility.

Examples:

- Review Packages;
- portfolio formats;
- historical snapshots;
- manifest records;
- SQLite schemas;
- public CLI behavior;
- timeline event payloads.

Breaking changes require:

- versioning;
- documentation;
- migration strategy;
- compatibility tests;
- clear deprecation policy.

Archived evidence must remain readable after current models evolve.

---

# 15. Reproducibility

Historical reviews should be reproducible.

Requirements:

- versioned schemas;
- deterministic serialization;
- archived evidence;
- preserved timestamps;
- preserved product version;
- stable snapshot identity;
- exact source bytes;
- explicit data-source metadata.

A historical result should be reproducible without relying on undocumented
memory or current external data.

---

# 16. Idempotence

Synchronization and import workflows should be safe to repeat.

Repeated execution should:

- skip already imported snapshot metadata;
- avoid duplicate detail rows;
- avoid duplicate timeline events;
- return a clear result;
- preserve existing history;
- not depend on manual cleanup.

Idempotence must be covered by automated tests.

---

# 17. Atomicity and Recovery

Multi-stage workflows must avoid misleading partial state.

Preferred mechanisms:

1. one database transaction where practical;
2. explicit compensating cleanup where component boundaries prevent one transaction;
3. preserved canonical snapshot metadata when the archive remains valid;
4. visible failure reporting.

Recovery procedures should be documented for:

- failed imports;
- damaged SQLite databases;
- invalid manifests;
- missing archive files;
- checksum mismatches.

---

# 18. Data Quality

Quality of data is more valuable than quantity.

Prefer:

- validated datasets;
- complete metadata;
- trusted sources;
- timezone-aware timestamps;
- explicit currencies;
- stable identifiers.

Reject incomplete or inconsistent data explicitly.

Never synthesize missing historical holdings, recommendations, or deployment
facts merely to populate a table.

---

# 19. Evidence Quality

Machine conclusions should distinguish:

- available evidence;
- missing evidence;
- stale evidence;
- conflicting evidence;
- verified evidence;
- unverified evidence.

Future confidence models must build upon preserved and traceable evidence.

Original source payloads should be retained where normalized columns cannot
preserve all analytical detail.

---

# 20. Security

Protect:

- credentials;
- personal portfolio information;
- local configuration;
- historical financial records;
- archive paths;
- database files.

Secrets must never be committed to version control.

Archive path handling must prevent traversal outside the configured history
root.

---

# 21. Privacy

User financial information belongs to the user.

Examples and fixtures should avoid unnecessary personal data.

Historical archives may contain sensitive portfolio information and should
remain local unless explicit synchronization features are introduced.

Future cloud or sharing capabilities require a separate privacy and threat
review.

---

# 22. Transparency

The system should communicate:

- missing data;
- stale data;
- assumptions;
- limitations;
- disconnected integrations;
- skipped imports;
- integrity failures;
- partially available history.

Transparency increases trust.

A workflow that imported only metadata must not appear equivalent to a fully
imported historical snapshot.

---

# 23. Observability

Important operations should be observable.

Typical events:

- review generation;
- snapshot archive;
- manifest registration;
- checksum verification;
- manifest synchronization;
- snapshot detail import;
- timeline creation;
- quote loading;
- portfolio import;
- validation failure;
- rollback or compensating cleanup.

CLI and future APIs should provide structured summaries suitable for logs and
automation.

---

# 24. Performance

Performance matters after correctness and integrity.

Preferred order:

1. Correctness
2. Integrity
3. Reliability
4. Maintainability
5. Performance

Optimize using measurements rather than assumptions.

Historical design should support:

- indexed date queries;
- indexed package queries;
- indexed symbol queries;
- incremental imports;
- safe batch operations.

Archive immutability must not be weakened for performance.

---

# 25. Scalability

The initial product is local-first, but historical volume will grow.

The design should scale through:

- date-partitioned archive folders;
- append-only manifest records;
- indexed SQLite tables;
- incremental synchronization;
- normalized structured storage;
- rebuildable projections.

Scalability changes must preserve compatibility with existing archives.

---

# 26. Portability

Core historical behavior should remain portable across supported operating
systems.

Requirements:

- safe path handling through `pathlib`;
- explicit UTF-8;
- normalized JSON;
- no dependence on platform-specific shell behavior;
- tests that avoid fixed absolute paths.

Line-ending differences must not affect historical checksums after a file is
archived because checksums apply to exact archived bytes.

---

# 27. Auditability

A reviewer should be able to determine:

- what was generated;
- when it was generated;
- when it was archived;
- which product version produced it;
- where it is stored;
- whether it was modified;
- what structured records were derived;
- what timeline events were generated.

Auditability does not require a full compliance product, but the architecture
must preserve these facts.

---

# 28. Schema Quality

Schemas are product contracts.

Quality requirements:

- explicit schema versions;
- documented fields;
- stable meanings;
- required constraints;
- migration planning;
- compatibility tests;
- no silent reinterpretation of existing columns.

Review Package schemas and SQLite schemas evolve independently and must not be
assumed to share the same version.

---

# 29. CLI Quality

CLI behavior should be:

- predictable;
- scriptable;
- explicit;
- backward compatible where practical;
- capable of structured JSON output;
- clear about skipped and failed work.

CLI modules should not contain domain logic.

Argument parsing errors and domain validation errors should produce actionable
messages.

---

# 30. Architecture Fitness Functions

Architecture should be reviewed continuously.

Questions include:

- Are domain boundaries respected?
- Are new circular dependencies introduced?
- Are canonical models preserved?
- Are public contracts still stable?
- Can historical data still be reproduced?
- Can SQLite be rebuilt from archive evidence?
- Are unverified files blocked from import?
- Are workflows idempotent?
- Are partial failures cleaned up?
- Are timestamps timezone-aware?
- Is original evidence preserved?

These questions should inform tests, code review, and documentation review.

---

# 31. Quality Gates

Before significant changes:

- focused tests pass;
- full regression tests pass;
- documentation is updated;
- public contracts are reviewed;
- architecture is respected;
- serialization is verified;
- historical compatibility is considered;
- migration impact is assessed;
- archive integrity behavior is tested.

For History-related changes, also verify:

- exact byte preservation;
- checksum behavior;
- duplicate protection;
- safe repeat execution;
- rollback behavior;
- timeline determinism.

---

# 32. Product Health Metrics

Useful indicators include:

- test coverage;
- regression failures;
- documentation freshness;
- architectural violations;
- technical debt;
- schema compatibility;
- failed imports;
- checksum failures;
- duplicate rejection counts;
- archive growth;
- timeline query performance.

Metrics guide discussion rather than replace engineering judgement.

---

# 33. Quality Review Checklist

Before accepting a major feature:

- Does it improve reliability?
- Is it deterministic?
- Does it preserve integrity?
- Is it testable?
- Can it be explained?
- Can it be archived?
- Can derived state be rebuilt?
- Is repeated execution safe?
- Are failure and rollback semantics clear?
- Is original evidence preserved?
- Is documentation updated?
- Is backward compatibility preserved?
- Are privacy and security implications understood?

---

# 34. Guiding Statements

> Reliability is more valuable than novelty.

> Integrity precedes convenience.

> Every important conclusion should be explainable.

> Preserve evidence before deriving knowledge.

> Missing evidence is itself valuable information.

> Canonical evidence must outlive derived databases.

> Rebuildability is a form of resilience.

> Quality compounds over time in the same way that technical debt does.

> Build a product that remains trustworthy long after individual implementations change.
