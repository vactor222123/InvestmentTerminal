# Investment Terminal — Architecture

## Status

**Product:** Investment Terminal  
**Document type:** High-level software architecture  
**Document status:** Foundational  
**Milestone:** 2 — Historical and Decision Intelligence  

This document defines the high-level architecture of Investment Terminal.

It describes:

- system boundaries;
- architectural layers;
- domains and responsibilities;
- data flow;
- dependency rules;
- storage responsibilities;
- integration points;
- reliability expectations;
- long-term evolution.

Detailed schemas belong in `DATA_MODEL.md`. Non-negotiable governance rules belong in `CONSTITUTION.md`. Product purpose belongs in `PROJECT_VISION.md`.

---

## Architectural Mission

Investment Terminal is designed as a long-term personal investment intelligence platform.

Its architecture must support a repeatable process:

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
Generate one review package
        ↓
Preserve immutable history
        ↓
Compare with previous states
        ↓
Create historical knowledge
        ↓
Support AI-assisted human judgment
```

The architecture is not optimized for automatic trading.

It is optimized for:

- data quality;
- traceability;
- reproducibility;
- explainability;
- historical integrity;
- modularity;
- maintainability;
- long-term product evolution.

---

# 1. System Context

Investment Terminal sits between external data sources and the final human investment decision.

```text
External data sources
        │
        ▼
Investment Terminal Python Engine
        │
        ├── structured current evidence
        ├── machine recommendations
        ├── portfolio analysis
        ├── historical snapshots
        └── confidence and limitations
        │
        ▼
investment_review_package.json
        │
        ▼
AI interpretation with current external context
        │
        ▼
Human investment decision
```

The Python engine creates deterministic evidence.

The AI layer interprets that evidence together with current context.

The user remains the final decision-maker.

---

# 2. High-Level Architecture

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
│                       STORAGE LAYER                         │
│ SQLite current data · Configuration files · Source traces  │
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
│ Holdings · Market value · Snapshot · Policy gap            │
│ Contribution planning · Position strategy · Risk context   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    DECISION INTELLIGENCE                    │
│ Machine recommendation · Deployment evidence · Confidence │
│ Decision trace · Warnings · Missing context                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       REVIEW LAYER                          │
│ Unified investment_review_package.json                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│ IMMUTABLE JSON ARCHIVE   │   │ STRUCTURED HISTORY SQLITE   │
│ Exact evidence snapshot  │   │ Queryable historical facts │
└─────────────┬────────────┘   └──────────────┬───────────────┘
              └──────────────┬────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    HISTORICAL INTELLIGENCE                  │
│ Diff · Transitions · Stability · Outcomes · Evolution      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      KNOWLEDGE LAYER                        │
│ Historical patterns · Factor effectiveness · Analogues     │
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

# 3. Architectural Layers

## 3.1 Configuration Layer

The configuration layer defines product behavior without containing business logic.

Responsibilities:

- environment configuration;
- database paths;
- source settings;
- portfolio settings;
- universe definitions;
- strategic allocation targets;
- documented thresholds;
- CLI defaults;
- feature flags where necessary.

Configuration must not become an untyped global dictionary shared across the codebase.

Important configuration should use explicit models or clearly named constants.

---

## 3.2 Data Acquisition Layer

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

## 3.3 Data Quality Layer

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

Data quality is a first-class domain rather than an implementation detail.

A downstream analysis must be able to distinguish:

- `READY`;
- `PARTIAL`;
- `STALE`;
- `MISSING`;
- `INVALID`;
- `NOT_CONNECTED`.

---

## 3.4 Current Storage Layer

Current operational data is stored separately from immutable historical evidence.

SQLite is the preferred source of truth for structured current market data and later structured history.

The storage layer may contain:

- completed market candles;
- validated fundamentals;
- instrument metadata;
- universe definitions;
- quote mappings;
- portfolio-related operational data;
- later, historical normalized records.

Files remain appropriate for:

- configuration;
- user-maintained portfolio input;
- stable exports;
- exact immutable review snapshots;
- fixtures and examples.

Excel must not be used as the primary database.

---

## 3.5 Analysis Layer

The analysis layer converts validated evidence into calculated evidence.

It contains independent domains such as:

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
- produce explicit typed outputs;
- remain deterministic;
- expose reason codes;
- expose coverage and limitations;
- avoid direct user-interface responsibilities.

---

## 3.6 Portfolio Intelligence Layer

The portfolio domain answers questions about assets actually owned by the user.

Core responsibilities:

- represent holdings;
- represent strategic policy;
- calculate cost basis;
- calculate current market value;
- classify holding strategy;
- calculate asset, sleeve, and strategy breakdowns;
- calculate policy gaps;
- plan new contributions at the strategic-bucket level;
- later, calculate performance, drawdown, concentration, and risk.

The portfolio domain must distinguish:

- `CORE_LONG_TERM`;
- `STOCK_LONG_TERM`;
- `POSITION_TRADE`;
- `CASH_RESERVE`.

Portfolio logic must not download market data directly.

It consumes quotes through provider interfaces.

---

## 3.7 Decision Intelligence Layer

The decision layer converts analysis into structured machine decision support.

Examples:

- machine recommendation;
- candidate priority;
- allocation gap;
- contribution plan;
- deployment mode;
- confidence;
- decision trace;
- warning severity.

This layer does not produce autonomous trades.

Its outputs must remain:

- explainable;
- versionable;
- serializable;
- reviewable;
- suitable for historical storage.

---

## 3.8 Review Layer

The review layer combines independently calculated sections into one product artifact:

```text
investment_review_package.json
```

The review layer is an assembler and adapter layer.

It must not:

- calculate indicators;
- download quotes;
- implement hidden recommendation rules;
- recreate portfolio calculations;
- silently discard errors.

It may:

- adapt typed domain objects to stable JSON;
- include section status;
- include source information;
- include missing-data information;
- preserve compatibility;
- expose one coherent interface to AI and history.

---

## 3.9 History Layer

The history layer preserves the state of each meaningful review.

It has two complementary storage forms.

### Exact JSON Archive

Purpose:

- preserve the exact generated package;
- allow future reproduction and inspection;
- retain fields that may not yet exist in normalized history tables.

Properties:

- immutable;
- timestamped;
- checksummed;
- schema-versioned;
- never overwritten.

### Structured History Database

Purpose:

- support fast queries;
- compare runs;
- track recommendation transitions;
- calculate portfolio evolution;
- evaluate historical outcomes.

The structured database is derived from exact snapshots but does not replace them.

---

## 3.10 Historical Intelligence Layer

This layer answers questions across multiple snapshots.

Responsibilities include:

- identify the previous compatible snapshot;
- calculate changes;
- detect recommendation transitions;
- measure signal duration;
- track ranking movement;
- track portfolio composition;
- track policy-gap movement;
- track confidence movement;
- evaluate future outcomes after historical signals.

History storage records facts.

Historical intelligence calculates relationships between those facts.

---

## 3.11 Knowledge Layer

The knowledge layer is a future domain built on sufficiently mature history.

It may generate structured knowledge such as:

- which combinations of factors were historically effective;
- which recommendation types were stable;
- which market regimes affected outcomes;
- which opportunities were repeatedly missed;
- which portfolio actions improved strategic alignment;
- which signals were unreliable under specific conditions.

Knowledge must remain:

- traceable to historical evidence;
- statistically honest;
- explicit about sample size;
- separated from unsupported inference;
- versioned when its calculation changes.

---

## 3.12 AI Interpretation Layer

AI consumes structured product evidence.

It may add current context such as:

- company and sector news;
- macroeconomic developments;
- central-bank decisions;
- political changes;
- geopolitical risks;
- scheduled events;
- contradictory narratives.

AI is not the source of truth for deterministic product facts.

AI must preserve the distinction between:

- package-derived facts;
- externally researched facts;
- inference;
- judgment;
- uncertainty.

---

## 3.13 CLI Layer

CLI modules are entry points.

They should perform only:

```text
Parse arguments
        ↓
Resolve dependencies and paths
        ↓
Call application services
        ↓
Render output
        ↓
Return an appropriate exit code
```

CLI modules must not become containers for domain logic.

Reusable logic belongs in services.

---

# 4. Domain Map

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

## Technical Domain

Owns:

- technical indicators;
- trend condition;
- momentum condition;
- volatility measures;
- technical evidence.

Does not own:

- downloads;
- portfolio allocation;
- external news interpretation.

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
- AI interpretation.

## Ranking Domain

Owns:

- candidate comparison;
- ranking order;
- component score aggregation;
- ranking reason data.

Does not own:

- final personal action;
- portfolio trade execution.

## Recommendation Domain

Owns:

- machine recommendation labels;
- recommendation reasons;
- recommendation warnings;
- coverage-aware adjustments;
- recommendation stability inputs.

Does not own:

- human final decisions;
- automatic orders.

## Portfolio Domain

Owns:

- holdings;
- policy;
- cash;
- market value;
- portfolio snapshots;
- policy gaps;
- contribution plans;
- holding strategies.

## Review Domain

Owns:

- unified package structure;
- section integration;
- package metadata;
- serialization boundaries;
- AI-facing export.

## History Domain

Owns:

- snapshot archiving;
- manifests;
- checksums;
- normalized historical records;
- previous-snapshot discovery.

## Decision Domain

Owns:

- deployment evidence;
- confidence;
- decision trace;
- machine-level action framing.

## Knowledge Domain

Owns future derived historical knowledge.

It must not mutate historical facts.

---

# 5. Primary Data Flows

## 5.1 Market Analysis Flow

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
Review-package sections
```

## 5.2 Portfolio Flow

```text
Portfolio JSON or CSV
        ↓
PortfolioHolding validation
        ↓
CurrentPortfolio
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
Contribution plan
        ↓
Review-package portfolio section
```

## 5.3 Historical Flow

```text
Completed review package
        ↓
Schema validation
        ↓
Checksum
        ↓
Immutable archive write
        ↓
Manifest update
        ↓
Structured history ingestion
        ↓
Previous compatible snapshot lookup
        ↓
Diff and transition generation
        ↓
Future knowledge analysis
```

## 5.4 AI Review Flow

```text
Current review package
        +
Historical summary or export
        +
Current external context
        ↓
Fact / signal / context separation
        ↓
Integrated interpretation
        ↓
Confidence and limitations
        ↓
Human final decision
```

---

# 6. Dependency Rules

Dependencies should flow inward toward stable domain models and services.

The following rules apply:

1. Acquisition may depend on provider contracts and source models.
2. Analysis may depend on validated domain evidence.
3. Portfolio may depend on quote-provider interfaces, not concrete downloaders.
4. Review may depend on domain outputs, not provider clients.
5. History may depend on stable serialized review contracts.
6. Knowledge may depend on history, never the reverse.
7. AI interpretation consumes review and history; deterministic domains do not depend on AI.
8. CLI may depend on application services; services must not depend on CLI.
9. Tests may depend on public interfaces and explicit fixtures.
10. Domain modules must not import unrelated CLI modules.

Forbidden dependency examples:

```text
Portfolio → Yahoo downloader
Review → RSI calculator
History → Market refresh
Fundamentals → Portfolio allocation
AI → mutate historical database
CLI → contain core scoring rules
```

---

# 7. Canonical Models and Sources of Truth

Investment Terminal must avoid multiple competing representations of the same concept.

Examples of canonical ownership:

- `PortfolioHolding` — one owned instrument;
- `CurrentPortfolio` — current owned positions and policy;
- `PortfolioMarketValueResult` — current priced portfolio state;
- recommendation result — machine recommendation source;
- `PortfolioPolicyGapResult` — strategic allocation difference;
- `ContributionPlan` — strategic use of available capital;
- `DeploymentDecision` — machine market-deployment evidence;
- review package — AI-facing current evidence interface;
- historical snapshot — immutable record of one generated package.

A JSON export is not a second business model.

It is a serialized representation of a canonical model.

---

# 8. Storage Architecture

## Operational SQLite

Used for current structured evidence, including completed candles and later other validated source data.

Properties:

- queryable;
- transactional;
- normalized where useful;
- replaceable through repeatable refresh logic;
- not itself the immutable review archive.

## Portfolio Configuration Files

Used for user-controlled portfolio input and examples.

Properties:

- human-readable;
- validated;
- explicit currencies and identifiers;
- separated from generated outputs.

## Review Exports

Used for current product output.

Properties:

- schema-versioned;
- complete enough for AI analysis;
- deterministic where inputs are unchanged;
- clear about missing sections.

## History Archive

Used for immutable exact evidence.

Properties:

- append-only;
- timestamped;
- checksum-protected;
- never silently overwritten.

## History SQLite

Used for historical queries and analytics.

Properties:

- linked to archived snapshot identity;
- migration-capable;
- rebuildable from immutable snapshots where feasible.

---

# 9. Error and Partial-Result Architecture

Investment Terminal distinguishes between:

- recoverable section failure;
- partial evidence;
- invalid configuration;
- unavailable external source;
- critical product failure.

A recoverable failure may allow package generation, but must produce structured status and warnings.

Example:

```json
{
  "status": "PARTIAL",
  "issues": [
    {
      "code": "QUOTE_NOT_FOUND",
      "symbol": "EMIMI",
      "severity": "WARNING",
      "effect": "Portfolio market value is incomplete."
    }
  ]
}
```

Critical failures include situations where:

- the package cannot be trusted;
- schema guarantees cannot be met;
- required identity or time metadata is missing;
- output would appear complete while being materially invalid.

No broad exception handler may silently convert arbitrary failures into `None`.

---

# 10. Confidence Architecture

Confidence is a separate future domain.

It must aggregate evidence quality rather than forecast profitability.

Potential components:

```text
Data quality
Data freshness
Source coverage
Fundamental coverage
Technical agreement
Trend stability
Portfolio fit
Market context
External context coverage
Historical consistency
Decision stability
```

The confidence architecture must support:

- component-level values;
- reason codes;
- penalties;
- missing components;
- weight versioning;
- overall explanation;
- product-wide consistent terminology.

Multiple unrelated confidence implementations are not permitted.

---

# 11. Decision Trace Architecture

Every important recommendation or deployment output should eventually reference a structured decision trace.

A trace may contain:

- decision identity;
- instrument;
- decision type;
- generated timestamp;
- input evidence references;
- positive reasons;
- negative reasons;
- warnings;
- thresholds;
- confidence;
- model version;
- previous decision;
- changed reasons.

Decision trace data must be included in history so future outcome analysis can evaluate not only the label, but the reasons behind it.

---

# 12. Security and Privacy Boundaries

The product may contain sensitive personal financial information.

Architecture must therefore prefer:

- local storage for portfolio data;
- no unnecessary transmission of raw personal data;
- explicit user action before sharing review packages externally;
- separation between example files and private files;
- secrets in environment variables or secure mechanisms;
- no credentials committed to Git;
- minimal connector permissions.

Future broker integration must use read-only access first.

Automatic trade permissions are outside the product scope.

---

# 13. Performance Philosophy

Correctness and traceability are more important than premature optimization.

Performance work should focus on:

- avoiding duplicate downloads;
- caching appropriate source data;
- incremental updates;
- efficient SQLite queries;
- batch processing;
- avoiding repeated serialization;
- bounded external requests.

Performance optimizations must not reduce explainability or historical integrity.

---

# 14. Test Architecture

The test structure should include:

- model validation tests;
- service unit tests;
- provider contract tests;
- importer and loader tests;
- serialization tests;
- CLI tests;
- package integration tests;
- regression tests;
- historical immutability tests;
- schema compatibility tests;
- deterministic timestamp tests.

External providers should be isolated behind interfaces and replaced with fakes in unit tests.

Every production bug should produce a regression test.

---

# 15. Repository Structure

The exact repository will evolve, but the intended domain structure is:

```text
InvestmentTerminal/
├── investment_terminal/
│   ├── cli/
│   ├── config/
│   ├── database/
│   ├── fundamentals/
│   ├── indicators/
│   ├── market/
│   ├── portfolio/
│   ├── ranking/
│   ├── recommendation/
│   ├── review/
│   ├── history/          # planned
│   ├── decision/         # may emerge from review services
│   ├── knowledge/        # future
│   └── common/           # only for truly shared contracts
├── data/
│   ├── portfolios/
│   ├── universes/
│   ├── market/
│   └── history/          # planned immutable archive
├── output/
├── tests/
├── docs/
│   ├── adr/
│   ├── PROJECT_VISION.md
│   ├── CONSTITUTION.md
│   ├── ARCHITECTURE.md
│   └── DATA_MODEL.md
└── README.md
```

New generic `utils` or `helpers` modules should be avoided unless responsibility is genuinely cross-domain and clearly named.

---

# 16. Current Architecture and Target Architecture

The product is in transition from its original architecture.

The original design emphasized:

- Finnhub;
- Yahoo Finance;
- SQLite;
- Excel reports;
- a central decision engine.

The current architecture has evolved toward:

- Yahoo-backed completed-candle storage;
- sector-aware fundamentals;
- ranking and coverage-aware recommendations;
- explicit portfolio models;
- strategy classification;
- market-value calculation;
- policy gaps;
- contribution planning;
- unified JSON review packages;
- external AI interpretation;
- planned immutable historical intelligence.

The new architecture does not discard the useful original principles:

- data quality first;
- automation before manual work;
- single source of truth;
- modular architecture;
- tests before release;
- no decisions from incomplete data.

It updates the system boundaries and product flow to match the actual long-term product.

---

# 17. Evolution Roadmap

```text
Foundation
    ↓
Documentation and architecture freeze
    ↓
Immutable historical journal
    ↓
Structured history database
    ↓
Diff and transition intelligence
    ↓
Decision trace
    ↓
Confidence framework
    ↓
Recommendation outcome analysis
    ↓
Knowledge engine
    ↓
AI-assisted personal investment operating system
```

Each stage must preserve compatibility with the prior evidence trail.

---

# 18. Architecture Quality Attributes

The architecture is evaluated against:

- reliability;
- explainability;
- traceability;
- reproducibility;
- determinism;
- maintainability;
- testability;
- extensibility;
- historical integrity;
- backward compatibility;
- security;
- operational transparency.

A new feature that improves functionality while materially damaging these attributes requires redesign.

---

# 19. Architecture Review Process

After approximately five to ten meaningful sprints, an architecture review should assess:

- whether domains remain focused;
- whether canonical models are duplicated;
- whether CLI logic has grown improperly;
- whether package schemas remain coherent;
- whether errors remain visible;
- whether history remains compatible;
- whether confidence logic is centralized;
- whether documentation matches code;
- whether any module should be simplified or removed.

Architecture review is a product-maintenance activity, not a failure response.

---

# 20. Guiding Architectural Statements

> Architecture exists to keep future development understandable.

> Data quality is part of product logic.

> Review Package is the interface between deterministic evidence and interpretation.

> History is a first-class product domain.

> Knowledge is derived from history; it never replaces history.

> AI consumes structured evidence; it does not become the source of deterministic facts.

> Clear responsibilities are preferred over clever coupling.

> Investment Terminal is a decision-support platform, not an autonomous trading system.
