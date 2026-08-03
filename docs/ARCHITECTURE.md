# Investment Terminal — Architecture

## Status

**Product:** Investment Terminal  
**Document type:** High-level software architecture  
**Document status:** Canonical  
**Milestone:** Sprint 12 — Historical Intelligence Foundation

This document defines the high-level architecture of Investment Terminal.

It describes:

- system boundaries;
- architectural layers;
- domains and responsibilities;
- dependency rules;
- primary data flows;
- current and historical storage;
- application services and CLI boundaries;
- reliability and integrity expectations;
- long-term evolution toward the Knowledge Domain.

Detailed schemas belong in `DATA_MODEL.md`. Non-negotiable governance rules belong in `CONSTITUTION.md`. Product purpose belongs in `PROJECT_VISION.md`.

---

# 1. Architectural Mission

Investment Terminal is a long-term personal investment intelligence platform.

Its architecture supports a repeatable evidence lifecycle:

```text
Collect evidence
        ↓
Validate evidence
        ↓
Normalize evidence
        ↓
Analyse evidence
        ↓
Evaluate the portfolio
        ↓
Build machine decision support
        ↓
Generate one Review Package
        ↓
Preserve immutable historical evidence
        ↓
Import structured history
        ↓
Build timeline events
        ↓
Compare historical states
        ↓
Create future knowledge
        ↓
Support AI-assisted human judgment
```

The architecture is not optimized for autonomous trading.

It is optimized for:

- correctness;
- determinism;
- data quality;
- traceability;
- reproducibility;
- explainability;
- historical integrity;
- modularity;
- maintainability;
- long-term product evolution.

The user remains the final decision-maker.

---

# 2. System Context

Investment Terminal sits between external data sources and the final human investment decision.

```text
External data sources
        │
        ▼
Investment Terminal Python Engine
        │
        ├── validated market evidence
        ├── portfolio state
        ├── analysis outputs
        ├── machine recommendations
        ├── deployment evidence
        ├── Review Packages
        └── historical records
        │
        ▼
Structured product artifacts
        │
        ├── current Review Package
        ├── immutable archive
        ├── append-only manifest
        ├── SQLite history
        └── timeline events
        │
        ▼
AI interpretation with current external context
        │
        ▼
Human investment decision
```

The Python engine creates deterministic and structured evidence.

The AI layer may interpret that evidence together with current context.

AI does not replace canonical calculations, archived facts, or the human decision.

---

# 3. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                    │
│ Market prices · Fundamentals · ETF data · Macro · Events   │
│ Portfolio files · Future broker connectors · News metadata │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA ACQUISITION                        │
│ Providers · Downloaders · Importers · Retry · Rate limits  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA QUALITY LAYER                       │
│ Validation · Freshness · Coverage · Normalization · Audit  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 CURRENT OPERATIONAL STORAGE                 │
│ Quotes · Candles · Fundamentals · Configuration · Mapping  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     ANALYSIS DOMAINS                        │
│ Technical · Fundamental · Market · Ranking · Recommendation│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    PORTFOLIO INTELLIGENCE                   │
│ Holdings · Market value · Policy gap · Contribution plan   │
│ Strategy breakdown · Risk context · Deployment constraints │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    DECISION INTELLIGENCE                    │
│ Recommendation · Allocation · Deployment · Confidence      │
│ Decision trace · Warnings · Missing context                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       REVIEW DOMAIN                         │
│ Unified investment_review_package.json                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       HISTORY DOMAIN                        │
│ Snapshot · Archive · Manifest · Verification · Import      │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
                ▼                               ▼
┌──────────────────────────┐      ┌───────────────────────────┐
│ IMMUTABLE JSON ARCHIVE   │      │ STRUCTURED HISTORY SQLITE│
│ Canonical evidence       │      │ Rebuildable projection   │
└───────────────┬──────────┘      └──────────────┬────────────┘
                └─────────────────┬───────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    HISTORICAL TIMELINE                      │
│ Snapshot · Portfolio · Holdings · Recommendation · Deploy  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FUTURE HISTORICAL INTELLIGENCE              │
│ Diff · Replay · Transitions · Stability · Outcomes         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FUTURE KNOWLEDGE DOMAIN                  │
│ Patterns · Evidence relationships · Confidence calibration │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI INTERPRETATION LAYER                   │
│ News · Macro · Politics · Geopolitics · Integrated review  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
                      Human final decision
```

---

# 4. Architectural Style

Investment Terminal uses a modular monolith with domain-oriented boundaries.

The project intentionally avoids premature distribution into services.

Primary characteristics:

- one deployable Python application;
- independent domain modules;
- explicit application services;
- clear serialization boundaries;
- local-first storage;
- CLI entry points;
- deterministic pipelines;
- rebuildable historical projections.

A module may depend on another domain only through explicit models, interfaces, or stable application contracts.

The modular monolith may later expose APIs or split infrastructure where justified, but domain boundaries must exist before deployment boundaries.

---

# 5. Architectural Layers

## 5.1 Configuration Layer

The configuration layer defines product behavior without containing business logic.

Responsibilities:

- environment configuration;
- database paths;
- data-source settings;
- portfolio settings;
- universe definitions;
- strategic allocation targets;
- documented thresholds;
- CLI defaults;
- feature flags where necessary.

Configuration must not become an untyped global dictionary shared across the codebase.

Important configuration should use explicit models or clearly named constants.

---

## 5.2 Data Acquisition Layer

The acquisition layer communicates with external or user-provided data sources.

Components may include:

- API clients;
- market-data downloaders;
- financial-statement clients;
- ETF metadata providers;
- CSV importers;
- JSON loaders;
- future broker connectors;
- future macro and event providers.

Responsibilities:

- request external data;
- handle transport errors;
- retry where appropriate;
- respect provider limitations;
- record source metadata;
- return raw or minimally parsed source results.

The acquisition layer must not:

- calculate investment scores;
- rank assets;
- create portfolio recommendations;
- decide deployment;
- silently convert failed downloads into valid-looking values.

---

## 5.3 Data Quality Layer

The data quality layer determines whether evidence is safe to use.

Responsibilities:

- schema validation;
- type validation;
- missing-value detection;
- market-session freshness;
- duplicate detection;
- coverage calculation;
- symbol resolution;
- currency validation;
- timestamp normalization;
- source traceability;
- structured warnings and errors.

Downstream analysis must be able to distinguish states such as:

```text
READY
PARTIAL
STALE
MISSING
INVALID
CONNECTED
NOT_CONNECTED
```

Missing evidence is data and must remain visible.

---

## 5.4 Current Operational Storage

Current operational data is separate from immutable historical evidence.

Current storage may contain:

- completed market candles;
- validated fundamentals;
- quote mappings;
- instrument metadata;
- universe definitions;
- portfolio-related operational data;
- local configuration;
- current exports.

Files remain appropriate for:

- configuration;
- user-maintained portfolio input;
- stable exports;
- fixtures and examples.

Excel is not the primary database.

Current operational storage may be replaced or rebuilt without changing the semantics of archived history.

---

## 5.5 Analysis Layer

The analysis layer converts validated evidence into calculated evidence.

It contains independent capabilities such as:

- technical analysis;
- fundamental analysis;
- valuation analysis;
- market breadth;
- market regime;
- sector-aware analysis;
- ranking;
- recommendation classification.

Each analysis service should:

- accept explicit validated inputs;
- produce explicit outputs;
- remain deterministic;
- expose reason codes;
- expose coverage and limitations;
- avoid direct presentation responsibilities.

---

## 5.6 Portfolio Intelligence Layer

The Portfolio Domain answers questions about assets owned by the user.

Responsibilities:

- represent holdings;
- represent strategic policy;
- calculate cost basis;
- calculate current market value;
- classify holding strategy;
- calculate asset and sleeve breakdowns;
- calculate policy gaps;
- plan new contributions;
- preserve portfolio constraints;
- later calculate performance, drawdown, and concentration.

Portfolio logic must not download market data directly.

It consumes quotes through explicit provider or repository boundaries.

---

## 5.7 Decision Intelligence Layer

The Decision Domain converts analysis into structured machine decision support.

Outputs may include:

- machine recommendation;
- candidate priority;
- allocation gap;
- contribution plan;
- deployment mode;
- confidence;
- rationale;
- decision trace;
- warning severity.

This layer does not execute trades.

Its outputs must remain:

- explainable;
- versionable;
- serializable;
- reviewable;
- suitable for historical storage.

---

## 5.8 Review Layer

The Review Domain combines independently calculated sections into one product artifact:

```text
investment_review_package.json
```

The Review Domain is an assembler and adapter boundary.

It must not:

- calculate indicators;
- download quotes;
- duplicate portfolio calculations;
- implement hidden recommendation rules;
- silently discard errors.

It may:

- adapt domain objects to stable JSON;
- include section statuses;
- include source metadata;
- include warnings and limitations;
- preserve compatibility;
- expose one coherent interface to AI and History.

---

## 5.9 History Layer

The History Domain preserves completed Review Packages as historical evidence.

Its responsibilities are divided into focused components:

```text
HistoricalSnapshot
HistoricalSnapshotArchive
HistoricalSnapshotManifest
HistoricalSnapshotService
HistoricalSQLiteStore
HistoricalSnapshotRepository
HistoricalManifestImportService
HistoricalReviewPackageLoader
HistoricalPortfolioSummaryImporter
HistoricalHoldingsImporter
HistoricalRecommendationsImporter
HistoricalDeploymentImporter
HistoricalTimelineBuilder
HistoricalImportPipeline
```

The History Domain owns:

- snapshot identity;
- immutable archive writing;
- exact-byte preservation;
- SHA-256 integrity;
- append-only manifest metadata;
- path safety;
- schema identity verification;
- structured historical import;
- timeline generation.

It does not own:

- technical analysis;
- portfolio calculations;
- recommendation generation;
- AI interpretation.

---

## 5.10 Application Services

Application services coordinate domain components.

Examples:

- snapshot preservation service;
- manifest synchronization service;
- historical import pipeline.

Application services may:

- orchestrate multiple domain operations;
- enforce workflow ordering;
- apply rollback or compensation;
- return structured results.

They must not duplicate lower-level validation or persistence rules.

---

## 5.11 CLI Layer

CLI modules are application entry points.

Their responsibilities are limited to:

```text
Parse arguments
        ↓
Resolve configuration and paths
        ↓
Construct dependencies
        ↓
Call application services
        ↓
Format results
        ↓
Return appropriate exit behavior
```

Current relevant CLIs include:

```text
investment_review_package.py
archive_review_package.py
import_history.py
```

CLI modules must not become containers for domain logic.

When orchestration grows, it belongs in an application service or pipeline.

---

## 5.12 Future Historical Intelligence Layer

Historical Intelligence operates across multiple snapshots.

Planned responsibilities:

- find previous compatible snapshots;
- compare portfolio states;
- calculate recommendation transitions;
- measure signal duration;
- track ranking movement;
- track portfolio composition;
- track deployment history;
- track confidence movement;
- evaluate outcomes after historical signals;
- support replay.

History stores and verifies facts.

Historical Intelligence calculates relationships between facts.

---

## 5.13 Future Knowledge Domain

The Knowledge Domain will be built only on mature historical evidence.

Possible responsibilities:

- historical pattern extraction;
- factor-effectiveness analysis;
- evidence relationships;
- recommendation stability;
- regime-aware observations;
- confidence calibration;
- decision-memory models.

Knowledge must remain:

- traceable to historical evidence;
- explicit about sample size;
- statistically honest;
- versioned when calculations change;
- separate from unsupported narrative inference.

Knowledge may be rebuilt.

Archived evidence may not be rewritten.

---

## 5.14 AI Interpretation Layer

AI consumes structured product evidence and may add current context such as:

- company and sector news;
- macroeconomic developments;
- central-bank decisions;
- political changes;
- geopolitical risks;
- scheduled events;
- contradictory narratives.

AI is not the Source of Truth for deterministic product facts.

AI must distinguish:

- package-derived facts;
- archived historical facts;
- externally researched facts;
- inference;
- judgment;
- uncertainty.

---

# 6. Domain Map

## Market Domain

Owns:

- instruments;
- prices;
- completed candles;
- quote resolution;
- trading sessions;
- freshness;
- market universes.

Does not own:

- portfolio policy;
- final recommendations;
- historical knowledge.

---

## Technical Domain

Owns:

- indicators;
- trend condition;
- momentum condition;
- volatility measures;
- technical evidence.

Does not own:

- market-data transport;
- portfolio allocation;
- AI interpretation.

---

## Fundamental Domain

Owns:

- financial metrics;
- sector-aware normalization;
- valuation evidence;
- financial-health evidence;
- fundamental coverage.

Does not own:

- technical indicators;
- portfolio positions;
- historical storage.

---

## Ranking Domain

Owns:

- candidate comparison;
- ranking order;
- component-score aggregation;
- ranking reason data.

Does not own:

- final human action;
- trade execution;
- snapshot archiving.

---

## Recommendation Domain

Owns:

- recommendation labels;
- recommendation reasons;
- warnings;
- coverage-aware adjustments;
- recommendation output.

Does not own:

- human final decisions;
- automatic orders;
- immutable history.

---

## Portfolio Domain

Owns:

- holdings;
- policy;
- cash;
- cost basis;
- market value;
- portfolio snapshots;
- policy gaps;
- contribution plans;
- holding strategies.

---

## Decision Domain

Owns:

- deployment evidence;
- confidence;
- decision trace;
- machine-level action framing.

---

## Review Domain

Owns:

- unified package structure;
- section integration;
- package metadata;
- serialization boundaries;
- AI-facing export.

---

## History Domain

Owns:

- historical snapshot identity;
- archive writing;
- manifest indexing;
- checksum verification;
- structured historical storage;
- timeline event generation.

The History Domain treats archived Review Package bytes as canonical evidence.

---

## Knowledge Domain

Owns future derived historical knowledge.

It must not mutate historical facts or become a parallel archive.

---

# 7. Primary Data Flows

## 7.1 Market Analysis Flow

```text
Universe definition
        ↓
Instrument resolution
        ↓
Market-data refresh
        ↓
Freshness and coverage validation
        ↓
Technical analysis
        ↓
Fundamental analysis
        ↓
Ranking
        ↓
Machine recommendations
        ↓
Review Package sections
```

---

## 7.2 Portfolio Flow

```text
Portfolio JSON or CSV
        ↓
Holding validation
        ↓
Current portfolio model
        ↓
Quote provider
        ↓
Portfolio market value
        ↓
Portfolio snapshot
        ↓
Strategy breakdown
        ↓
Policy gap
        ↓
Contribution or deployment plan
        ↓
Review Package portfolio section
```

---

## 7.3 Review Flow

```text
Analysis-domain outputs
        +
Portfolio-domain outputs
        +
Decision-domain outputs
        ↓
Review adapters
        ↓
Review Package builder
        ↓
Validated JSON export
```

The Review Package is the stable handoff artifact between current-state analysis, History, AI interpretation, and future integrations.

---

## 7.4 Snapshot Preservation Flow

```text
Completed Review Package
        ↓
Read exact bytes
        ↓
Validate package identity
        ↓
Generate snapshot UUID
        ↓
Calculate SHA-256
        ↓
Exclusive archive write
        ↓
Create HistoricalSnapshot metadata
        ↓
Append manifest record
```

If manifest registration fails, an unregistered archive created by that operation is removed.

Existing historical evidence is never modified.

---

## 7.5 Manifest Synchronization Flow

```text
manifest.jsonl
        ↓
Load canonical snapshot metadata
        ↓
Check SQLite repository
        ↓
Select missing snapshots
        ↓
Atomic metadata insertion
        ↓
ManifestImportResult
```

Repeated execution is safe.

---

## 7.6 Historical Import Flow

```text
Registered HistoricalSnapshot
        ↓
Resolve safe archive path
        ↓
Read exact bytes
        ↓
Verify SHA-256
        ↓
Validate JSON identity
        ↓
Import portfolio summary
        ↓
Import holdings
        ↓
Import recommendations
        ↓
Import deployment
        ↓
Build timeline events
```

If detail import fails, partial detail rows are removed while valid snapshot metadata remains registered.

---

## 7.7 AI Review Flow

```text
Current Review Package
        +
Relevant historical evidence
        +
Current external research
        ↓
AI synthesis
        ↓
Explicit facts, inference, uncertainty, and scenarios
        ↓
Human judgment
```

---

# 8. Historical Storage Architecture

Sprint 12 established three distinct historical representations.

## 8.1 Immutable Archived Review Package

Default location:

```text
data/history/YYYY/MM/<snapshot-file>.json
```

Purpose:

- preserve exact evidence;
- retain all source fields;
- support later verification;
- support future replay;
- survive SQLite schema changes.

Properties:

- immutable;
- exact-byte preservation;
- SHA-256 identified;
- schema-versioned;
- timezone-aware metadata;
- never overwritten.

This is the canonical historical Source of Truth.

---

## 8.2 Append-only Manifest

Default location:

```text
data/history/manifest.jsonl
```

Purpose:

- index archived snapshots;
- expose archive location;
- preserve package and product identity;
- support synchronization;
- support search by snapshot or package.

Properties:

- append-only;
- duplicate protected;
- human inspectable;
- independent from SQLite;
- rebuild support for structured history.

---

## 8.3 Structured History SQLite

Default location:

```text
data/history/history.db
```

Current schema:

```text
schema_metadata
snapshots
portfolio_summary
holdings
recommendations
deployment
timeline_events
```

Purpose:

- efficient search;
- normalized historical queries;
- future comparison;
- timeline filtering;
- historical analytics;
- future Knowledge projections.

Properties:

- rebuildable;
- indexed;
- foreign-key constrained;
- schema-versioned;
- not canonical evidence.

---

# 9. Source-of-Truth Rules

The canonical hierarchy is:

```text
Immutable archived Review Package
        ↓
Append-only manifest metadata
        ↓
Rebuildable SQLite history
        ↓
Derived timeline and future knowledge
```

Rules:

1. Archived JSON is canonical historical evidence.
2. Manifest is the canonical append-only snapshot index.
3. SQLite is a normalized projection.
4. Timeline events are derived records.
5. Future knowledge is a derived interpretation.
6. Derived data must not introduce facts absent from source evidence.
7. SQLite may be rebuilt without altering the archive.
8. A checksum mismatch blocks import.
9. No consumer outside the History Domain should depend directly on archive folder layout.

---

# 10. Dependency Rules

Allowed dependency direction:

```text
CLI
 ↓
Application Services / Pipelines
 ↓
Domain Services and Repositories
 ↓
Models and Infrastructure Adapters
```

Domain dependency principles:

- Market may be consumed by Portfolio and Analysis.
- Analysis may feed Recommendation and Review.
- Portfolio may feed Decision and Review.
- Decision may feed Review.
- Review may feed History.
- History may feed future Historical Intelligence and Knowledge.
- Knowledge must not mutate Review or History.
- AI may consume outputs but must not become a dependency of deterministic domains.

Forbidden patterns:

- business rules in CLI;
- History importing analysis internals;
- Portfolio directly calling external APIs;
- Review recalculating domain values;
- Knowledge rewriting historical records;
- circular imports between domains;
- hidden shared mutable state.

---

# 11. Integrity and Reliability Boundaries

Historical operations must verify:

- safe relative paths;
- archive-root containment;
- file existence;
- exact SHA-256;
- UTF-8 encoding;
- valid JSON;
- object structure;
- schema identity;
- generated timestamp identity;
- foreign-key integrity;
- duplicate constraints.

Workflow reliability requires:

- explicit failures;
- idempotent synchronization;
- repeat-import protection;
- deterministic ordering;
- database transactions where practical;
- compensating cleanup where a single transaction is not available;
- structured result objects.

A partially imported snapshot must not be reported as fully imported.

---

# 12. Schema Evolution

Review Package schemas and SQLite schemas evolve independently.

Requirements:

- every persistent schema has a version;
- old archives remain readable;
- breaking changes require migration or compatibility adapters;
- new importers must handle supported historical shapes explicitly;
- timeline payload semantics must remain documented;
- schema migrations must be introduced before SQLite schema version 2.

The exact archived package must remain available even when normalized tables change.

---

# 13. Testing Architecture

Tests should mirror architectural responsibilities.

Expected test categories:

- domain invariant tests;
- archive exact-byte tests;
- checksum and path-safety tests;
- manifest append and duplicate tests;
- repository atomicity tests;
- importer normalization tests;
- rollback tests;
- idempotence tests;
- timeline determinism tests;
- pipeline integration tests;
- CLI tests;
- full regression tests.

Preferred progression:

```text
Focused module test
        ↓
Domain integration test
        ↓
CLI or workflow test
        ↓
Full pytest suite
```

External internet access should not be required for deterministic unit and History tests.

---

# 14. Current CLI Workflows

Generate current Review Package:

```powershell
python -m investment_terminal.cli.investment_review_package
```

Archive Review Package:

```powershell
python -m investment_terminal.cli.archive_review_package
```

Synchronize and import history:

```powershell
python -m investment_terminal.cli.import_history
```

Metadata-only synchronization:

```powershell
python -m investment_terminal.cli.import_history --metadata-only
```

Current workflow remains intentionally explicit:

```text
Generate
    ↓
Archive
    ↓
Import
```

Direct automatic archival from the existing Review Package CLI is deferred until a stable orchestration boundary is implemented.

---

# 15. Current Architectural Limitations

The following capabilities are not yet complete:

- direct Review Package generation-to-archive orchestration;
- public timeline query repository;
- historical replay service;
- snapshot comparison service;
- recommendation transition analysis;
- outcome tracking;
- import-state table;
- SQLite migration framework;
- archive integrity audit CLI;
- manifest rebuild tooling;
- Knowledge Domain implementation.

These are planned extensions of the current architecture, not reasons to replace it.

---

# 16. Evolution Path

## Near-term

- align `DATA_MODEL.md`;
- align `DOMAIN_MAP.md`;
- align `ROADMAP.md`;
- add timeline query APIs;
- add replay support;
- add snapshot comparison;
- add schema migration foundation;
- test the History pipeline with real generated Review Packages.

## Medium-term

- portfolio evolution queries;
- recommendation history;
- deployment outcome tracking;
- confidence history;
- transition models;
- evidence relationships.

## Long-term

- Knowledge Domain;
- pattern extraction;
- decision memory;
- confidence calibration;
- AI synthesis grounded in archived evidence.

---

# 17. Architectural Decision Guidance

A new feature should be placed by asking:

- Is it raw evidence acquisition?
- Is it validation?
- Is it deterministic analysis?
- Is it portfolio logic?
- Is it decision logic?
- Is it review assembly?
- Is it historical preservation?
- Is it cross-snapshot intelligence?
- Is it derived knowledge?
- Is it only presentation or CLI behavior?

If a feature performs more than one of these responsibilities, it should usually be decomposed.

---

# 18. Architectural Invariants

The following rules are non-negotiable:

1. The user remains the final decision-maker.
2. Deterministic calculations stay outside AI.
3. Review assembles; it does not recreate analysis.
4. Historical evidence is immutable.
5. Archived JSON is canonical historical evidence.
6. SQLite history is rebuildable.
7. Verification occurs before historical derivation.
8. CLI contains no domain business logic.
9. Missing data remains explicit.
10. New capabilities extend domain boundaries rather than bypass them.
11. Future knowledge must remain traceable to evidence.
12. No historical correction silently overwrites prior history.

---

# 19. Guiding Statement

> Investment Terminal should preserve not only what the system believes now, but what it believed before, which evidence supported it, and how that belief changed over time.

The architecture must make this possible without sacrificing correctness, traceability, or maintainability.
