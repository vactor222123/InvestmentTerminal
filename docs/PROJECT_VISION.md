# Investment Terminal — Project Vision

## Status

**Product:** Investment Terminal  
**Product type:** Long-term personal investment intelligence platform  
**Document status:** Foundational  
**Milestone:** 2 — Historical and Decision Intelligence  

This document defines why Investment Terminal exists, what long-term product it is intended to become, and which outcomes guide its development.

It is a product-vision document rather than an implementation specification. Technical design belongs in `ARCHITECTURE.md`, data contracts belong in `DATA_MODEL.md`, and non-negotiable rules belong in `CONSTITUTION.md`.

## Mission

Investment Terminal helps its user make more disciplined, transparent, and evidence-based investment decisions by collecting, validating, processing, structuring, and preserving financial information.

Investment Terminal does not attempt to predict the future with certainty.

It reduces uncertainty by:

- improving the quality and completeness of available evidence;
- separating facts, machine-generated signals, external context, and final judgment;
- explaining why a signal or recommendation exists;
- tracking how portfolios, markets, and recommendations change over time;
- preserving historical decisions and their supporting evidence;
- enabling later analysis of which signals, conditions, and decisions were effective.

## Product Vision

Investment Terminal is a **personal investment intelligence platform**, not merely a stock screener, portfolio tracker, or trading signal generator.

The long-term product should support the complete investment-review process:

```text
Market and portfolio data
        ↓
Validation and normalization
        ↓
Technical and fundamental analysis
        ↓
Portfolio and allocation analysis
        ↓
Machine evidence and decision support
        ↓
Historical preservation and change detection
        ↓
External context and AI-assisted interpretation
        ↓
Explainable human investment judgment
```

The product should become more useful over time because it accumulates structured history and transforms that history into knowledge.

## Primary User Outcome

The primary outcome is not “find the asset with the highest score.”

The primary outcome is to help the user answer practical investment questions such as:

- What changed since the previous review?
- What is the current condition of the portfolio?
- Where does the portfolio differ from its strategic allocation?
- How should new capital be distributed?
- Should capital be deployed now, partially deployed, or held?
- Which assets deserve further investigation?
- Which positions should be held, accumulated, reduced, or reviewed?
- Why did a recommendation change?
- How strong and complete is the supporting evidence?
- Which risks, assumptions, and missing data affect the conclusion?
- How did similar signals perform historically?
- Which past decisions were effective, and under which conditions?

## Investment Scope

The product is intended to support a diversified long-term personal portfolio that may include:

- broad-market ETFs;
- regional and emerging-market ETFs;
- bond ETFs and other defensive assets;
- thematic ETFs with long-term development potential;
- individual long-term stock positions;
- position trades with holding periods from approximately one month to several months;
- cash reserves for corrections, drawdowns, and future opportunities;
- additional asset classes introduced in later product stages.

The platform must remain independent of a single broker, market-data provider, exchange, or fixed number of instruments.

## Strategic Portfolio Intent

The preferred high-level portfolio structure is approximately:

```text
80%  long-term core assets
10%  individual stocks and tactical positions
10%  cash reserve
```

These are strategic targets, not automatic trading commands.

The system must distinguish between:

- `CORE_LONG_TERM`;
- `STOCK_LONG_TERM`;
- `POSITION_TRADE`;
- `CASH_RESERVE`.

Each strategy may require different entry, holding, risk, review, and exit rules.

## Core Product Responsibilities

### 1. Data Collection

The platform should collect and maintain structured evidence from available sources, including:

- market prices and completed candles;
- technical indicators;
- company fundamentals;
- valuation metrics;
- portfolio holdings and cost basis;
- current portfolio market values;
- ETF characteristics;
- market breadth and regime indicators;
- watchlists and opportunity universes;
- macroeconomic data;
- event and earnings metadata;
- news and geopolitical metadata where technically and legally appropriate.

### 2. Data Quality

The system must verify that evidence is:

- present;
- correctly typed and normalized;
- sufficiently complete;
- fresh for its intended use;
- traceable to its source;
- safe for JSON serialization and historical storage.

A missing or unreliable value must not be silently converted into a confident conclusion.

### 3. Structured Analysis

The platform should calculate and expose:

- technical condition;
- fundamental quality;
- valuation condition;
- risk factors;
- ranking;
- machine recommendations;
- portfolio composition;
- strategic allocation gaps;
- contribution plans;
- deployment evidence;
- confidence components;
- historical changes;
- recommendation stability;
- later, historical recommendation accuracy.

### 4. Review Package Generation

The program must combine relevant evidence into one stable, machine-readable file:

```text
investment_review_package.json
```

This file is the primary interface between the deterministic Python system and the external interpretation layer.

It should eventually contain enough structured evidence for a high-quality investment review without requiring the user to manually assemble multiple files.

### 5. Historical Intelligence

Every meaningful review should be preservable as an immutable historical snapshot.

History is not only a backup mechanism.

It should support:

- changes since the previous run;
- recommendation transitions;
- portfolio evolution;
- signal duration;
- factor stability;
- historical outcome measurement;
- discovery of recurring conditions;
- creation of evidence-based product knowledge.

### 6. Explainable Decision Support

The product may generate machine recommendations and deployment modes, but every output must remain explainable.

A decision-support object should make clear:

- **what** the output is;
- **why** it was generated;
- **which evidence** supports it;
- **which evidence conflicts with it**;
- **how complete and consistent** the evidence is;
- **which risks and limitations** remain;
- **what external context** still requires review.

## Separation of Responsibilities

### Python Responsibilities

Python is responsible for deterministic and reproducible work:

- collecting data;
- validating data;
- normalizing data;
- calculating indicators and scores;
- applying documented business rules;
- generating machine evidence;
- preserving history;
- identifying changes;
- producing stable structured files.

Python does not possess final human judgment and does not claim certainty about future outcomes.

### AI Responsibilities

The AI interpretation layer is responsible for combining structured program output with current external context, including:

- recent news;
- macroeconomic developments;
- monetary policy;
- geopolitical developments;
- relevant scheduled events;
- conflicting narratives and uncertainty;
- relationships that are difficult to encode as stable deterministic rules.

AI must not silently rewrite source data or present assumptions as facts.

### Human Responsibilities

The user remains the final decision-maker.

Investment Terminal supports judgment; it does not replace it.

The product must preserve the difference between:

- factual evidence;
- calculated signals;
- external context;
- interpretation;
- final personal action.

## Confidence Vision

Confidence is a central product concept.

**Confidence does not mean the probability of future profit.**

Confidence measures the quality, completeness, freshness, consistency, and agreement of the available evidence.

The future confidence framework should be decomposable into components such as:

- data quality;
- data freshness;
- fundamental coverage;
- technical agreement;
- trend stability;
- portfolio fit;
- market-regime coverage;
- news coverage;
- macroeconomic coverage;
- geopolitical-context coverage;
- historical consistency;
- decision stability.

A confidence value must always be accompanied by its components, reasons, limitations, and missing evidence.

## Knowledge Loop

The long-term product operates as a knowledge loop:

```text
Data
  ↓
Validated evidence
  ↓
Analysis
  ↓
Review package
  ↓
Immutable history
  ↓
Outcome measurement
  ↓
Historical patterns
  ↓
Product knowledge
  ↓
Better-informed future reviews
```

The system does not “learn” by inventing rules from a few examples.

Knowledge must be derived from sufficiently complete, traceable, and explainable historical evidence.

## Product Values

When product trade-offs arise, Investment Terminal prefers:

- reliability over feature count;
- explainability over unnecessary complexity;
- evidence over unsupported opinion;
- data quality over fast output;
- explicit uncertainty over false precision;
- modularity over tightly coupled convenience;
- long-term maintainability over short-term shortcuts;
- immutable history over destructive updates;
- human judgment over automatic execution;
- a stable data contract over ad hoc output formats.

## Non-Goals

Investment Terminal is not intended to:

- guarantee profit;
- predict markets with certainty;
- present confidence as a probability of success;
- replace a licensed financial adviser;
- make legal, tax, or regulated suitability determinations;
- execute trades automatically;
- operate as a high-frequency trading system;
- hide logic in unexplained black-box scores;
- recommend action from incomplete or stale evidence without warnings;
- optimize solely for short-term returns;
- treat every market movement as an actionable signal.

These non-goals may only be changed through an explicit architecture decision and product review.

## Long-Term Product Stages

### Stage 1 — Foundation

- market-data ingestion;
- technical analysis;
- fundamental analysis;
- ranking;
- machine recommendations;
- portfolio representation;
- portfolio market value;
- review-package generation.

### Stage 2 — Historical Intelligence

- immutable review archive;
- history manifest;
- SQLite history;
- change detection;
- recommendation transitions;
- portfolio evolution;
- decision trace;
- historical comparison.

### Stage 3 — Decision Intelligence

- confidence framework;
- market regime;
- contribution planning;
- deployment evidence;
- position sizing;
- risk analysis;
- ETF and thematic opportunity analysis;
- watchlist intelligence.

### Stage 4 — Knowledge Intelligence

- recommendation outcome measurement;
- factor effectiveness;
- signal lifetime;
- recurring-condition analysis;
- historical analogues;
- strategy-specific evidence;
- personal investment knowledge base.

### Stage 5 — AI-Assisted Investment Review

- one-command evidence generation;
- one structured review package;
- external context integration;
- explainable portfolio review;
- opportunity and risk interpretation;
- documented final human decision;
- periodic investment reports.

### Stage 6 — Personal Investment Operating System

The mature product should support a repeatable workflow:

```text
investment-terminal review
```

The command should eventually:

- refresh required data;
- validate freshness and coverage;
- analyse relevant universes;
- evaluate the current portfolio;
- generate policy gaps and contribution evidence;
- determine machine deployment evidence;
- compare the current run with history;
- archive the new snapshot;
- update the historical database;
- produce one final review package.

## Definition of Product Success

Investment Terminal is successful when it helps the user make investment decisions that are:

- more disciplined;
- better documented;
- less impulsive;
- more transparent;
- based on higher-quality evidence;
- consistent with the user’s long-term strategy;
- reviewable after the fact;
- capable of improving through historical evaluation.

Success is not defined by whether every recommendation is profitable.

Success is defined by whether the product continuously improves the quality of the decision process.

## Product Commitment

Investment Terminal is treated as a long-term product.

New modules should not be added merely because they are technically interesting.

Every meaningful addition must answer a concrete investment question, improve data quality, improve explainability, improve decision quality, or create useful historical knowledge.

The guiding statement is:

> **Investment Terminal does not attempt to predict the future. It reduces uncertainty by collecting the highest-quality available evidence, explaining its signals, and accumulating its own historical experience.**
