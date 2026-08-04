# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 12 — Historical Intelligence Foundation  
**Current development branch:** `develop`

---

# 1. Purpose

This roadmap defines the intended development direction of Investment Terminal.

It is not a fixed promise of dates.

It establishes:

- product sequencing;
- architectural priorities;
- domain maturity;
- quality gates;
- expected sprint outcomes;
- long-term product direction.

The roadmap should be updated when architecture or priorities materially change.

---

# 2. Product Vision

Investment Terminal is being developed as a long-term private investment intelligence platform.

The product should be able to:

- collect validated market and company data;
- model the user's portfolio;
- calculate deterministic technical and fundamental evidence;
- rank investment candidates;
- generate explainable recommendations;
- support allocation and deployment decisions;
- assemble structured Review Packages;
- preserve every meaningful review as immutable evidence;
- compare present and historical states;
- derive traceable knowledge from accumulated history;
- support AI-assisted human judgment.

The user remains responsible for the final investment decision.

---

# 3. Development Principles

Every milestone must protect:

1. correctness;
2. determinism;
3. historical integrity;
4. explainability;
5. maintainability;
6. backward compatibility;
7. testability.

No sprint is complete until:

- focused tests pass;
- the full regression suite passes;
- documentation is aligned;
- the working tree is clean;
- changes are committed and pushed;
- unfinished integration is removed or explicitly deferred.

---

# 4. Product Evolution

```text
Foundation
    ↓
Current-State Analysis
    ↓
Portfolio and Decision Intelligence
    ↓
Unified Review Package
    ↓
Historical Intelligence Foundation
    ↓
Historical Comparison and Replay
    ↓
Outcome Analysis and Confidence
    ↓
Knowledge Domain
    ↓
Evidence-Grounded AI Experience
```

---

# 5. Completed Foundations

## Early Foundation

Completed capabilities include:

- Python project structure;
- configuration;
- logging;
- SQLite support;
- file-based inputs;
- market-data integration;
- portfolio loading;
- test infrastructure;
- CLI workflows;
- structured exports.

---

## Current-State Analysis Foundation

Implemented capabilities include:

- market-data models;
- quote providers;
- technical indicators;
- stock-analysis data;
- ranking inputs;
- machine recommendations;
- portfolio holdings;
- portfolio policy;
- cost-basis snapshots;
- market-value enrichment;
- contribution planning;
- Review Package generation.

---

# 6. Sprint 11 — Architecture and Documentation Foundation

**Status:** Completed

Sprint 11 established the canonical product and engineering documentation.

Delivered documents include:

- `PROJECT_VISION.md`;
- `CONSTITUTION.md`;
- `ARCHITECTURE.md`;
- `DATA_MODEL.md`;
- `INVESTMENT_PHILOSOPHY.md`;
- `DEVELOPMENT_GUIDELINES.md`;
- `DESIGN_PRINCIPLES.md`;
- `QUALITY_ATTRIBUTES.md`;
- `PRODUCT_VALUES.md`;
- `GLOSSARY.md`;
- `DOMAIN_MAP.md`;
- Architecture Decision Records;
- `SPRINT_11_REVIEW.md`;
- `SPRINT_12_PLAN.md`.

Primary outcome:

> Investment Terminal moved from an evolving collection of modules to a documented product architecture with explicit domain boundaries and engineering rules.

---

# 7. Sprint 12 — Historical Intelligence Foundation

**Status:** Implementation complete  
**Documentation status:** Final alignment in progress

Sprint 12 introduced the first complete History Domain.

## Delivered Capabilities

- canonical `HistoricalSnapshot`;
- immutable Review Package archive;
- exact-byte preservation;
- SHA-256 integrity;
- safe archive paths;
- append-only `manifest.jsonl`;
- snapshot preservation service;
- archive CLI;
- SQLite history schema;
- snapshot repository;
- manifest-to-SQLite synchronization;
- verified archived-package loader;
- portfolio-summary importer;
- holdings importer;
- recommendations importer;
- deployment importer;
- timeline-event builder;
- end-to-end historical import pipeline;
- History import CLI;
- Sprint 12 architecture review.

## Historical Data Flow

```text
Review Package
        ↓
Immutable Archive
        ↓
Append-only Manifest
        ↓
Verified Loading
        ↓
Structured SQLite Import
        ↓
Timeline Events
```

## Sprint 12 Outcome

Investment Terminal can now preserve a completed review as:

- immutable evidence;
- verifiable evidence;
- indexed evidence;
- normalized historical data;
- timeline events.

## Deferred from Sprint 12

- direct automatic archival from Review Package generation;
- public timeline query service;
- historical replay;
- snapshot comparison;
- schema migration framework;
- explicit import-state model;
- archive audit and manifest rebuild tools.

These are planned extensions of the implemented foundation.

---

# 8. Sprint 12 Closure Checklist

Before Sprint 12 is formally closed:

- run the complete test suite;
- confirm a clean Git working tree;
- confirm archive smoke test;
- confirm import smoke test;
- align canonical documentation;
- commit and push all documentation updates;
- verify that `SPRINT_12_REVIEW.md` reflects the final status.

Recommended validation:

```powershell
python -m pytest
git status
```

---

# 9. Sprint 13 — Historical Query and Replay Foundation

**Status:** Planned

## Goal

Make the History Domain usable for structured historical inspection, comparison, and replay.

## Proposed Scope

### 9.1 Timeline Repository

Implement a public query boundary for:

- chronological event listing;
- filtering by snapshot;
- filtering by event type;
- filtering by subject key;
- filtering by date range;
- retrieving latest events;
- deterministic pagination or bounded results.

### 9.2 Snapshot Listing

Add a clean public repository method for:

- listing all snapshots;
- chronological ordering;
- latest snapshot;
- package-lineage history;
- generated-date filtering.

This removes direct SQL access from CLI code.

### 9.3 Import-State Model

Introduce explicit historical import state.

Potential states:

```text
METADATA_ONLY
VERIFIED
IMPORTING
IMPORTED
FAILED
```

Potential fields:

- snapshot ID;
- metadata synchronized at;
- package verified at;
- details imported at;
- timeline built at;
- failure reason;
- importer version.

### 9.4 Snapshot Comparison Foundation

Implement first comparison models:

- earlier snapshot;
- later snapshot;
- compatibility result;
- portfolio-summary change;
- holdings added;
- holdings removed;
- holdings-value changes;
- recommendation changes;
- deployment changes.

### 9.5 Historical Replay

Define replay semantics.

Replay must distinguish:

- exact archived evidence;
- normalized historical view;
- recalculation using current code;
- current external context.

### 9.6 End-to-End History Tests

Use a real generated Review Package fixture to validate:

```text
Generate
    ↓
Archive
    ↓
Manifest
    ↓
Import
    ↓
Timeline
    ↓
Query
```

## Expected Sprint 13 Deliverables

- timeline repository;
- snapshot list API;
- import-state schema and repository;
- snapshot comparison model;
- first comparison service;
- replay contract;
- CLI query commands;
- complete tests;
- `SPRINT_13_REVIEW.md`.

---

# 10. Sprint 14 — Historical Portfolio Analytics

**Status:** Planned

## Goal

Turn normalized historical portfolio data into useful portfolio-evolution analysis.

## Proposed Scope

- total portfolio-value timeline;
- invested-value timeline;
- cash timeline;
- sleeve-weight evolution;
- strategy-weight evolution;
- holding quantity evolution;
- holding value evolution;
- position additions and removals;
- concentration history;
- contribution history;
- policy-gap history.

## Expected Outputs

```text
PortfolioEvolutionSeries
HoldingEvolutionSeries
AllocationEvolutionSeries
PolicyGapEvolutionSeries
```

## Quality Requirements

- all calculations trace to snapshots;
- no invented values;
- explicit cost-basis versus market-value status;
- deterministic date ordering;
- compatibility checks between snapshots.

---

# 11. Sprint 15 — Recommendation and Deployment History

**Status:** Planned

## Goal

Analyze how machine recommendations and deployment decisions change over time.

## Proposed Scope

- recommendation transition model;
- action-change detection;
- score movement;
- confidence movement;
- rationale change;
- recommendation duration;
- repeated recommendation stability;
- deployment allocation history;
- capital-allocation transitions;
- recommendation-to-deployment relationship.

## Example Transitions

```text
WATCH → BUY
BUY → HOLD
HOLD → REDUCE
NOT_CONNECTED → CONNECTED
```

## Expected Outputs

- recommendation transition timeline;
- per-symbol recommendation history;
- deployment history;
- stability indicators;
- change explanations.

---

# 12. Sprint 16 — Outcome Tracking and Confidence Foundation

**Status:** Planned

## Goal

Evaluate what happened after prior recommendations without pretending that historical association proves causation.

## Proposed Scope

- future-price outcome windows;
- recommendation outcome models;
- deployment outcome models;
- benchmark-relative results;
- drawdown after recommendation;
- confidence dimensions;
- evidence completeness;
- source freshness;
- signal agreement;
- historical support;
- sample-size visibility.

## Confidence Principle

Confidence must not be one unexplained number.

It should expose dimensions such as:

- completeness;
- freshness;
- consistency;
- historical support;
- sample size;
- conflict level.

## Expected Outputs

```text
RecommendationOutcome
DeploymentOutcome
ConfidenceResult
EvidenceCoverage
```

---

# 13. Sprint 17 — Historical Intelligence Services

**Status:** Planned

## Goal

Create higher-level services that answer cross-snapshot questions.

## Proposed Scope

- previous-compatible-snapshot discovery;
- historical analogues;
- trend persistence;
- recurring portfolio imbalances;
- repeated missed opportunities;
- repeated recommendation reversals;
- regime-aware history;
- stability and transition summaries.

## Example Questions

- How long has this recommendation remained unchanged?
- When did this holding first appear?
- How has the portfolio's cash weight changed?
- Which recommendations frequently reversed?
- Which deployment plans were repeatedly deferred?
- Which signals were reliable only in specific regimes?

---

# 14. Sprint 18 — Knowledge Domain Foundation

**Status:** Planned

## Goal

Introduce traceable product knowledge derived from verified historical evidence.

## Proposed Scope

- `EvidenceReference`;
- `KnowledgeEntry`;
- evidence relationship graph;
- knowledge calculation version;
- sample-size requirements;
- confidence and limitation fields;
- knowledge supersession;
- knowledge repository;
- knowledge rebuild pipeline.

## Knowledge Rules

- knowledge must reference evidence;
- knowledge must expose sample size;
- knowledge must be versioned;
- knowledge must not rewrite history;
- unsupported inference must remain clearly identified;
- weak evidence must not be presented as certainty.

---

# 15. Later Product Capabilities

## Evidence-Grounded AI

- current Review Package interpretation;
- historical evidence retrieval;
- traceable knowledge retrieval;
- external current-context research;
- facts versus inference separation;
- scenario generation;
- explainable multi-period review.

## Portfolio Risk

- concentration risk;
- drawdown;
- volatility;
- correlations;
- currency exposure;
- sector exposure;
- risk-budget constraints.

## Multi-Account and Broker Integration

- multiple broker accounts;
- broker instrument mapping;
- automated portfolio import;
- transaction history;
- tax-lot data;
- reconciliation.

## Reporting and User Experience

- interactive dashboard;
- portfolio evolution charts;
- recommendation timeline;
- audit reports;
- notifications;
- scheduled review workflows.

---

# 16. Long-Term Possibilities

Potential future capabilities include:

- dividend calendar;
- tax reporting;
- multi-broker support;
- options analysis;
- selected crypto support;
- real-estate investment module;
- macroeconomic dashboard;
- scenario simulation;
- portfolio stress testing;
- personalized evidence search;
- local-first web interface;
- automated scheduled reviews.

These possibilities must not weaken the core product principles.

---

# 17. Capabilities Not Prioritized

Investment Terminal is not currently prioritizing:

- autonomous trading;
- high-frequency trading;
- hidden black-box recommendations;
- social trading;
- gamified speculation;
- unsupported predictive certainty;
- cloud dependence;
- rewriting historical facts.

---

# 18. Release Strategy

Development flow:

```text
Focused task
    ↓
Focused tests
    ↓
Full regression suite
    ↓
Documentation update
    ↓
Commit to develop
    ↓
Architecture review
    ↓
Sprint review
    ↓
Release candidate
```

Possible product stages:

```text
Development
    ↓
Alpha
    ↓
Beta
    ↓
Stable
```

Release readiness depends on quality, not only feature count.

---

# 19. Success Criteria

The product is progressing successfully when it can:

- update and validate current evidence;
- model the user's portfolio;
- explain deterministic recommendations;
- generate a complete Review Package;
- preserve reviews immutably;
- verify historical integrity;
- rebuild structured history;
- compare portfolio and recommendation states;
- track historical outcomes honestly;
- derive knowledge with traceable evidence;
- support AI interpretation without giving AI ownership of facts;
- operate without hidden manual data manipulation.

---

# 20. Roadmap Review Rules

This document should be reviewed:

- after every completed sprint;
- after a major architectural decision;
- when a domain changes maturity;
- when a planned feature is deferred;
- when scope is added or removed;
- before starting a new multi-sprint milestone.

When reality differs from the roadmap, update the roadmap.

Do not preserve outdated plans merely for appearance.

---

# 21. Current Next Step

After Sprint 12 documentation is fully aligned, the next formal activity should be:

```text
Sprint 13 Planning
```

The recommended Sprint 13 theme is:

> Historical Query, Comparison, and Replay Foundation

Before implementation begins, create:

```text
docs/SPRINT_13_PLAN.md
```

The plan should define:

- scope;
- explicit non-goals;
- task sequence;
- schema changes;
- compatibility requirements;
- testing strategy;
- documentation updates;
- Definition of Done.

---

# 22. Final Direction

> Investment Terminal should evolve from current-state analysis into a system that preserves evidence, compares history, evaluates outcomes, and derives knowledge without losing traceability.

The roadmap therefore follows this sequence:

```text
Evidence
    ↓
Decision Support
    ↓
Review
    ↓
History
    ↓
Comparison
    ↓
Outcomes
    ↓
Knowledge
    ↓
Evidence-Grounded AI
```
