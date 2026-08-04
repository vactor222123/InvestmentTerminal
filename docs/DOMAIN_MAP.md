# DOMAIN_MAP.md

# Investment Terminal — Domain Map

**Status:** Canonical Architecture Map  
**Updated after:** Sprint 12 — Historical Intelligence Foundation

---

# 1. Purpose

This document defines the business domains of Investment Terminal, their responsibilities, boundaries, dependencies, owned data, produced outputs, consumed inputs, and evolution rules.

A domain owns a business capability. Infrastructure supports domains but does not own business meaning.

---

# 2. High-Level Domain Map

```text
External Data Sources
        ↓
Market Data
        ↓
Technical / Fundamental Analysis
        ↓
Ranking and Recommendation
        ↓
Portfolio
        ↓
Decision
        ↓
Review
        ↓
History
        ↓
Historical Intelligence (future)
        ↓
Knowledge (future)
        ↓
AI Interpretation
        ↓
Human Decision
```

Supporting boundaries:

```text
Configuration · Infrastructure · CLI · Serialization · Persistence · Logging
```

---

# 3. Domain Overview

| Domain | Status | Primary Responsibility |
|---|---|---|
| Market Data | Implemented | Validated prices, candles, instruments, freshness |
| Technical Analysis | Implemented | Deterministic indicators and signals |
| Fundamental Analysis | Implemented | Company-quality and valuation evidence |
| Ranking | Implemented | Compare and order candidates |
| Recommendation | Implemented | Produce deterministic recommendations |
| Portfolio | Implemented | Holdings, policy, market value, allocation, contribution planning |
| Decision | Developing | Deployment evidence and decision-support framing |
| Review | Implemented | Assemble the canonical Review Package |
| History | Implemented in Sprint 12 | Preserve, verify, index, import, and timeline historical evidence |
| Historical Intelligence | Planned | Compare snapshots and analyze transitions |
| Knowledge | Planned | Derive reusable patterns from verified history |
| AI Interpretation | External layer | Add current context and narrative synthesis |
| Infrastructure | Supporting boundary | Filesystem, SQLite, CLI, configuration, logging |

---

# 4. Market Data Domain

## Purpose

Provide validated market facts.

## Owns

- instruments and exchange metadata;
- quotes and completed candles;
- trading-session context;
- freshness and source metadata;
- quote repositories and providers.

## Consumes

- external market APIs;
- local market-data files;
- instrument configuration;
- exchange mappings.

## Produces

- validated quotes;
- validated price history;
- freshness status;
- source trace;
- instrument resolution.

## Does Not Own

- portfolio allocation;
- technical indicators;
- recommendations;
- deployment decisions;
- historical snapshots.

---

# 5. Technical Analysis Domain

## Purpose

Transform validated price history into deterministic technical evidence.

## Owns

- RSI, SMA, EMA, MACD, ATR;
- volume and 52-week metrics;
- trend, momentum, and volatility states;
- technical reason codes.

## Consumes

- validated market-price history;
- instrument metadata;
- explicit analysis configuration.

## Produces

- technical indicators;
- technical signals;
- technical coverage and limitations.

## Does Not Own

- market-data transport;
- portfolio holdings;
- final recommendations;
- archive storage;
- AI narrative.

---

# 6. Fundamental Analysis Domain

## Purpose

Transform validated company data into structured fundamental evidence.

## Owns

- valuation, growth, profitability, and financial-health metrics;
- sector-aware normalization;
- fundamental coverage and reason data.

## Consumes

- validated company fundamentals;
- company and sector metadata;
- normalization rules.

## Produces

- fundamental signals;
- valuation and quality evidence;
- missing-data status;
- structured limitations.

## Does Not Own

- technical indicators;
- portfolio positions;
- final recommendation labels;
- historical storage;
- AI interpretation.

---

# 7. Ranking Domain

## Purpose

Compare candidates using deterministic evidence.

## Owns

- ranking rules;
- candidate comparison;
- component-score aggregation;
- ranking order and tie-breaking;
- ranking reason data.

## Consumes

- technical evidence;
- fundamental evidence;
- market context;
- optional portfolio constraints.

## Produces

- ordered candidates;
- ranking scores;
- ranking explanations;
- coverage-aware ranking results.

## Does Not Own

- final human action;
- portfolio mutation;
- trade execution;
- historical snapshot creation.

---

# 8. Recommendation Domain

## Purpose

Convert deterministic evidence into machine recommendation outputs.

## Owns

- recommendation labels;
- rationale and warnings;
- coverage-aware adjustments;
- score interpretation;
- recommendation compatibility rules.

## Consumes

- technical signals;
- fundamental signals;
- ranking outputs;
- market and optional portfolio context.

## Produces

- symbol and action;
- score and confidence inputs;
- rationale and warning state.

## Does Not Own

- final human decision;
- order execution;
- portfolio mutation;
- archive storage;
- AI-generated facts.

---

# 9. Portfolio Domain

## Purpose

Represent and analyze the user's current portfolio.

## Owns

- portfolio identity and policy;
- holdings and instrument keys;
- cash balance and cost basis;
- market value;
- asset, sleeve, and strategy breakdowns;
- policy gaps;
- contribution planning;
- portfolio constraints.

## Consumes

- portfolio input files;
- validated quotes through provider interfaces;
- strategic-policy configuration.

## Produces

- `CurrentPortfolio`;
- `PortfolioSnapshot`;
- market-value result;
- policy-gap result;
- contribution plan;
- portfolio section for Review.

## Does Not Own

- direct market-data downloads;
- technical indicators;
- final stock recommendations;
- immutable historical archives;
- AI interpretation.

---

# 10. Decision Domain

## Purpose

Combine recommendation evidence and portfolio context into structured decision support.

## Owns

- deployment evidence;
- allocation framing;
- capital-deployment records;
- decision trace;
- warning severity;
- confidence inputs;
- machine-level action framing.

## Consumes

- recommendation outputs;
- portfolio state and policy gaps;
- contribution plans;
- market context;
- later historical evidence and knowledge.

## Produces

- allocation and deployment plans;
- decision-support payload;
- structured rationale;
- confidence-related evidence.

## Does Not Own

- trade execution;
- autonomous portfolio mutation;
- market-data acquisition;
- archive verification;
- final human judgment.

---

# 11. Review Domain

## Purpose

Assemble independently produced domain outputs into one stable product artifact.

## Owns

- Review Package structure;
- package schema version;
- section integration and metadata;
- serialization boundary;
- AI-facing export;
- section statuses and warnings.

## Consumes

- market, technical, fundamental, ranking, recommendation, portfolio, and decision outputs;
- source metadata.

## Produces

```text
investment_review_package.json
```

## Does Not Own

- indicator calculations;
- quote downloads;
- portfolio calculations;
- recommendation rules;
- historical archiving;
- knowledge extraction.

## Boundary Rule

Review assembles. Review does not recreate domain logic.

---

# 12. History Domain

## Purpose

Preserve completed Review Packages as immutable, verifiable, indexed, and queryable historical evidence.

## Status

Implemented in Sprint 12.

## Owns

- `HistoricalSnapshot` and snapshot identity;
- immutable archive writing and exact-byte preservation;
- SHA-256 checksums and archive-path safety;
- append-only manifest;
- SQLite history schema and snapshot repository;
- manifest synchronization;
- verified package loading;
- portfolio-summary, holdings, recommendations, and deployment import;
- timeline-event generation;
- historical import pipeline.

## Consumes

- completed Review Package;
- archive-root, manifest, and SQLite configuration.

## Produces

- archived JSON;
- manifest records;
- normalized snapshot metadata;
- historical portfolio, holdings, recommendations, deployment, and timeline records;
- import reports.

## Does Not Own

- current portfolio calculations;
- indicator or recommendation generation;
- market-data acquisition;
- AI interpretation;
- pattern analysis across snapshots.

## Internal Components

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

## Source-of-Truth Rule

```text
Archived JSON
    canonical historical evidence

manifest.jsonl
    append-only snapshot index

history.db
    rebuildable structured projection
```

## Future Evolution

- import-state model;
- archive audit and manifest rebuild;
- schema migration;
- replay support;
- timeline query repository.

---

# 13. Historical Intelligence Domain

## Purpose

Analyze relationships across multiple verified snapshots.

## Status

Planned.

## Will Own

- snapshot comparison;
- recommendation transitions;
- portfolio and deployment evolution;
- signal duration and ranking movement;
- outcome analysis;
- replay semantics.

## Will Consume

- History Domain records and timeline events;
- archived packages where exact evidence is required.

## Will Produce

- comparison results;
- transition records;
- evolution series;
- replay reports;
- historical-performance relationships.

## Must Not Own

- archive mutation;
- current recommendation generation;
- market-data acquisition;
- unsupported narrative inference.

---

# 14. Knowledge Domain

## Purpose

Derive reusable, traceable knowledge from verified historical evidence.

## Status

Planned.

## Will Own

- evidence relationships;
- historical patterns;
- factor-effectiveness observations;
- recommendation stability knowledge;
- regime-aware findings;
- confidence calibration;
- knowledge-entry versioning.

## Will Consume

- Historical Intelligence outputs;
- History Domain evidence references;
- sample-size and coverage metadata.

## Will Produce

- traceable knowledge entries;
- confidence evidence;
- historical analogues;
- product learning.

## Boundary Rule

Knowledge learns from History. Knowledge never rewrites History.

---

# 15. AI Interpretation Layer

## Purpose

Interpret structured product evidence together with current external context.

## Consumes

- current Review Package;
- selected historical evidence;
- future Knowledge outputs;
- current news, macro, political, and geopolitical context.

## Produces

- explanation;
- synthesis;
- scenarios;
- uncertainty framing;
- human-readable review.

## Does Not Own

- canonical calculations;
- historical facts;
- archive identity;
- deterministic recommendation rules;
- final decision.

---

# 16. Infrastructure Boundary

## Purpose

Provide technical mechanisms required by domains.

## Owns Technical Mechanisms

- filesystem access;
- SQLite connections;
- JSON serialization;
- CLI argument parsing;
- logging;
- configuration loading;
- process exit behavior.

## Does Not Own Business Meaning

Infrastructure must not decide what a recommendation means, how portfolio allocation works, or how historical evidence is interpreted.

---

# 17. CLI Boundary

CLI is an application boundary rather than a business domain.

Current CLI flows:

```text
investment_review_package.py
archive_review_package.py
import_history.py
```

CLI responsibilities:

- parse arguments;
- resolve paths;
- construct dependencies;
- call application services;
- format results;
- expose actionable errors.

CLI must not contain domain calculations or persistence invariants.

---

# 18. Allowed Dependencies

```text
Market Data
    ↓
Technical / Fundamental Analysis
    ↓
Ranking
    ↓
Recommendation
    ↓
Decision
```

```text
Market Data
    ↓
Portfolio
    ↓
Decision
```

```text
Analysis + Portfolio + Decision
            ↓
          Review
            ↓
          History
            ↓
Historical Intelligence
            ↓
         Knowledge
            ↓
    AI Interpretation
```

Application direction:

```text
CLI
    ↓
Application Services / Pipelines
    ↓
Domain Services / Repositories
    ↓
Models and Infrastructure Adapters
```

---

# 19. Forbidden Dependencies

```text
History → Market API
History → Technical indicator calculation
Portfolio → External API directly
Review → Indicator calculation
Review → Portfolio recalculation
Knowledge → Snapshot modification
Historical Intelligence → Archive mutation
Decision → Automatic portfolio mutation
Infrastructure → Business-rule ownership
CLI → Domain-rule implementation
AI → Canonical historical rewrite
```

Circular dependencies between domains are forbidden.

---

# 20. Data Ownership Matrix

| Data Concept | Owning Domain |
|---|---|
| Instrument metadata | Market Data |
| Quote and candle | Market Data |
| Technical indicator | Technical Analysis |
| Fundamental metric | Fundamental Analysis |
| Ranking result | Ranking |
| Recommendation | Recommendation |
| Portfolio holding and policy | Portfolio |
| Contribution plan | Portfolio |
| Deployment evidence | Decision |
| Review Package | Review |
| Historical snapshot | History |
| Archived JSON | History |
| Manifest record | History |
| SQLite historical records | History |
| Timeline event | History |
| Snapshot comparison | Historical Intelligence |
| Knowledge entry | Knowledge |
| AI narrative | AI Interpretation |

Ownership determines who validates, changes, and documents a concept.

---

# 21. Domain Input and Output Matrix

| Domain | Consumes | Produces |
|---|---|---|
| Market Data | External market sources | Quotes, candles, freshness |
| Technical | Price history | Indicators and technical signals |
| Fundamental | Company data | Fundamental evidence |
| Ranking | Analysis evidence | Ordered candidates |
| Recommendation | Signals and ranking | Recommendation outputs |
| Portfolio | Holdings, policy, quotes | Snapshot, gaps, contribution plan |
| Decision | Recommendation and portfolio context | Deployment evidence |
| Review | Domain outputs | Review Package |
| History | Review Package | Archive, manifest, SQLite history, timeline |
| Historical Intelligence | Historical records | Comparisons and transitions |
| Knowledge | Historical intelligence | Traceable knowledge |
| AI | Product evidence and external context | Human-readable synthesis |

---

# 22. Source-of-Truth Map

| Information | Source of Truth |
|---|---|
| Current market quote | Market Data repository/provider |
| Current holdings | Portfolio input and canonical portfolio model |
| Current recommendation | Recommendation Domain output |
| Current Review Package | Review Domain artifact |
| Historical Review Package | Immutable archived JSON |
| Snapshot metadata index | Append-only manifest |
| Queryable historical projection | SQLite history |
| Timeline | Derived History Domain events |
| Historical comparison | Historical Intelligence result |
| Knowledge | Versioned Knowledge Domain output |

Important rule:

```text
SQLite is not the only copy of historical evidence.
```

---

# 23. Sprint 12 Additions

Sprint 12 introduced and implemented:

- History Domain;
- `HistoricalSnapshot`;
- immutable snapshot archive;
- append-only manifest;
- snapshot preservation service;
- archive CLI;
- SQLite history schema;
- snapshot repository;
- manifest synchronization;
- verified historical package loader;
- portfolio-summary, holdings, recommendations, and deployment importers;
- timeline builder;
- historical import pipeline;
- History import CLI.

History is no longer planned. It is now an implemented first-class domain.

---

# 24. Domain Maturity

| Domain | Maturity |
|---|---|
| Market Data | Established |
| Technical Analysis | Established |
| Fundamental Analysis | Established |
| Ranking | Established |
| Recommendation | Established |
| Portfolio | Established |
| Decision | Developing |
| Review | Established |
| History | Foundation implemented |
| Historical Intelligence | Planned |
| Knowledge | Planned |
| AI Interpretation | External integration layer |

---

# 25. Evolution Rules

Create a new domain only when a distinct business responsibility emerges.

Prefer extending an existing domain when ownership remains clear, the same invariants apply, and no circular dependency is introduced.

Create a new domain when the concept has its own lifecycle, owns distinct data, requires independent rules, or serves different consumers.

---

# 26. Architecture Review Questions

Before introducing a change, ask:

- Which domain owns this capability?
- Which domain owns the resulting data?
- What does it consume and produce?
- Does it duplicate another domain?
- Does it violate dependency direction?
- Can it be tested independently?
- Does it preserve historical integrity?
- Is it deterministic?
- Is it current-state, historical, or knowledge logic?
- Is the CLI only orchestrating?
- Is the Source of Truth explicit?

---

# 27. Guiding Statements

> Domains own business capabilities.

> Models represent business concepts.

> Services implement behaviour.

> Review assembles information.

> History preserves and verifies evidence.

> Historical Intelligence compares evidence.

> Knowledge learns from verified history.

> AI interprets but does not rewrite facts.

> Decision support assists the investor.

> The investor remains responsible for final action.

> Architecture should become clearer as the product evolves.
