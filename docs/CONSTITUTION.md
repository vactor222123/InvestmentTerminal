# Investment Terminal — Constitution

## Status

**Product:** Investment Terminal  
**Document type:** Foundational governance document  
**Document status:** Binding  
**Milestone:** 2 — Historical and Decision Intelligence  

This document defines the non-negotiable principles that govern the design, development, operation, and evolution of Investment Terminal.

`PROJECT_VISION.md` explains why the product exists. This Constitution defines the rules that must remain true while the product evolves.

Any exception to this document requires:

1. an explicit Architecture Decision Record;
2. a documented reason;
3. an analysis of risks and alternatives;
4. confirmation that the change still supports the product mission.

---

# Article 1 — Mission Before Features

Every feature, module, data source, score, recommendation, export, and workflow must support the mission of Investment Terminal:

> **Reduce uncertainty through high-quality evidence, explainable analysis, structured history, and disciplined decision support.**

A feature must not be added solely because it is technically interesting.

A new module must improve at least one of the following:

- data quality;
- evidence coverage;
- explainability;
- portfolio understanding;
- decision quality;
- historical knowledge;
- operational reliability;
- product maintainability.

If it improves none of these, it should not be built.

---

# Article 2 — Investment Questions Come First

Every meaningful module must answer a concrete investment question.

Examples include:

- What is the current state of the portfolio?
- Which parts of the portfolio differ from strategic targets?
- How should new capital be distributed?
- Should capital be deployed now, partially deployed, or held?
- Which assets deserve further review?
- What changed since the previous run?
- Why did a recommendation change?
- How complete and consistent is the evidence?
- How did similar recommendations perform historically?

Implementation begins only after the question is clearly defined.

The system must not accumulate disconnected indicators, scores, or services without a documented decision purpose.

---

# Article 3 — Python Structures, AI Interprets, Humans Decide

## 3.1 Python Responsibilities

Python performs deterministic and reproducible work:

- data collection;
- data validation;
- normalization;
- calculations;
- technical analysis;
- fundamental analysis;
- portfolio analysis;
- ranking;
- machine evidence generation;
- structured export;
- history preservation;
- change detection;
- documented rule application.

Python may generate decision-support labels such as:

- `BUY`;
- `ACCUMULATE`;
- `WATCH`;
- `HOLD`;
- `AVOID`;
- `SELL`;
- `INVEST_NOW`;
- `PARTIAL_DEPLOYMENT`;
- `WAIT`.

These labels are machine outputs, not final personal investment decisions.

## 3.2 AI Responsibilities

AI interprets structured evidence and current external context.

AI may:

- explain relationships between evidence;
- add current news, macroeconomic, political, and geopolitical context;
- identify conflicts and uncertainty;
- compare alternatives;
- formulate a final review for the user.

AI must not:

- silently alter source data;
- present assumptions as verified facts;
- hide missing evidence;
- treat machine confidence as a guaranteed outcome;
- replace the user's final judgment.

## 3.3 Human Responsibility

The user remains the final decision-maker.

Investment Terminal is a decision-support system, not an autonomous investment authority.

---

# Article 4 — Evidence Before Opinion

Every conclusion must be traceable to evidence.

The system must distinguish between:

- raw facts;
- validated facts;
- calculated metrics;
- machine signals;
- external context;
- interpretation;
- final human action.

Unsupported statements must not be presented as evidence-based conclusions.

When evidence is incomplete, contradictory, stale, or unavailable, the system must say so explicitly.

---

# Article 5 — Explainability Over Complexity

A simpler transparent model is preferred over a more complex opaque model when both provide similar decision value.

Every important output must answer:

- What is the output?
- Why was it generated?
- Which evidence supports it?
- Which evidence conflicts with it?
- What is missing?
- What risks remain?
- How confident is the system in the evidence?
- What alternatives exist?

No score, classification, confidence value, or recommendation may exist as an unexplained “magic number.”

---

# Article 6 — Confidence Measures Evidence Quality

Confidence is not the probability of future profit.

Confidence measures the quality of the available evidence.

Confidence may include components such as:

- completeness;
- freshness;
- source reliability;
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

Every overall confidence result must be decomposable.

A confidence value must be accompanied by:

- component scores;
- supporting reasons;
- penalties;
- missing data;
- limitations;
- warnings.

The system must avoid false precision.

---

# Article 7 — Data Quality Is a First-Class Requirement

The system must not treat data collection as successful merely because a value exists.

Evidence must be evaluated for:

- correctness;
- type safety;
- freshness;
- completeness;
- expected market session;
- source;
- duplicate handling;
- missing values;
- currency;
- resolution;
- timestamp;
- applicable domain rules.

No silent failures are permitted.

Recoverable failures may produce partial results, but the failure must remain visible in structured form.

---

# Article 8 — Stable Data Contracts

Machine-readable outputs are product interfaces.

Key formats, including `investment_review_package.json`, must use:

- explicit schema versions;
- stable field names;
- documented semantics;
- ISO 8601 timestamps;
- explicit currencies;
- explicit statuses;
- structured warnings;
- structured missing-data information;
- backward-compatible changes when reasonably possible.

Breaking changes require:

- a schema-version change;
- migration guidance;
- tests;
- documentation;
- an Architecture Decision Record when the impact is significant.

Historical files must remain understandable after the product evolves.

---

# Article 9 — History Is Immutable

Historical snapshots are append-only.

A historical review package must not be overwritten because a newer result exists.

If a correction is required, the system should create:

- a new corrected snapshot;
- a link to the superseded snapshot;
- a reason for the correction.

History must preserve:

- the evidence available at the time;
- the calculations used at the time;
- the schema version;
- the product version where available;
- the generated timestamp;
- the supporting recommendation reasons;
- the warnings and limitations.

History is not merely backup storage.

History exists to create future knowledge.

---

# Article 10 — Reproducibility

Given the same:

- input data;
- configuration;
- schema version;
- business rules;
- product version;

the deterministic Python system should produce the same output.

Every important calculation must have:

- defined inputs;
- defined outputs;
- documented rules;
- deterministic tests;
- stable rounding rules where financial values are involved.

External context may change over time, but the original evidence and original result must remain recoverable.

---

# Article 11 — Decision Trace Is Mandatory

Every recommendation or deployment signal must preserve a decision trace.

The trace should include, where applicable:

- recommendation;
- previous recommendation;
- reason codes;
- positive factors;
- negative factors;
- risk factors;
- missing evidence;
- confidence components;
- thresholds used;
- data timestamp;
- model or rule version;
- relevant portfolio context.

A future reviewer must be able to understand why the system produced the result.

---

# Article 12 — No Automatic Trading

Investment Terminal must not execute trades automatically.

The system may produce:

- suggested actions;
- candidate lists;
- allocation gaps;
- contribution plans;
- deployment modes;
- position-size evidence;
- warnings;
- review priorities.

Execution remains outside the system unless this Constitution is explicitly amended through a major governance decision.

This rule exists to preserve:

- human judgment;
- operational safety;
- accountability;
- reviewability;
- separation between analysis and execution.

---

# Article 13 — Portfolio Strategy Must Be Explicit

Portfolio recommendations must be interpreted within the user's strategy.

The current strategic intent is approximately:

```text
80%  CORE_LONG_TERM
10%  STOCK_LONG_TERM and POSITION_TRADE
10%  CASH_RESERVE
```

The system must distinguish between:

- long-term core assets;
- long-term individual stocks;
- position trades;
- cash reserves.

Different strategies must not share identical rules merely because they involve the same ticker.

A long-term investment and a position trade may require different:

- time horizons;
- entry logic;
- exit logic;
- risk limits;
- review frequency;
- confidence requirements.

---

# Article 14 — Context Must Not Be Hidden

Market, macroeconomic, political, geopolitical, and event context may materially affect interpretation.

When external context is unavailable, the system must say so.

A machine recommendation based only on price, fundamentals, and technicals must not be presented as a complete final recommendation.

The review package should state which context layers are:

- connected;
- partially connected;
- missing;
- externally required.

---

# Article 15 — Partial Results Must Be Honest

A partial result is acceptable when full data is unavailable.

A misleading complete-looking result is not acceptable.

Partial outputs must include:

- status;
- missing sections;
- affected symbols;
- fallback logic;
- warnings;
- effect on confidence;
- whether action should be delayed.

Fallbacks must be explicit.

For example, cost basis may temporarily replace market value, but the output must identify that limitation.

---

# Article 16 — No Unexplained Thresholds

Thresholds, weights, ranges, penalties, and classifications must be documented.

Examples include:

- score boundaries;
- freshness limits;
- allocation tolerances;
- confidence penalties;
- deployment-breadth thresholds;
- position-size limits;
- valuation bands.

Every threshold should have:

- a name;
- a purpose;
- a documented source or rationale;
- tests;
- an owner or module;
- a path for future review.

Thresholds must not be scattered as undocumented literals throughout the codebase.

---

# Article 17 — Modularity and Domain Boundaries

The product is divided into domains such as:

- market;
- fundamentals;
- technical analysis;
- ranking;
- recommendations;
- portfolio;
- review;
- history;
- decision intelligence;
- external context;
- knowledge.

Each domain must have a clear responsibility.

A domain must not directly absorb unrelated responsibilities for convenience.

Examples:

- portfolio logic must not become news analysis;
- history storage must not decide recommendations;
- AI interpretation must not silently become the source of raw market data;
- CLI code must not contain hidden domain logic.

Dependencies should flow through documented interfaces.

---

# Article 18 — Tests Are Part of the Product

A feature is not complete without tests.

Tests should cover:

- successful behavior;
- validation failures;
- boundary conditions;
- backward compatibility;
- partial data;
- missing data;
- serialization;
- deterministic calculations;
- financial rounding where relevant;
- schema stability;
- historical immutability.

A passing test suite does not prove investment correctness, but it is required for engineering reliability.

---

# Article 19 — Documentation Is a Product Artifact

Documentation is not optional maintenance work.

The following documents are part of the product:

- `PROJECT_VISION.md`;
- `CONSTITUTION.md`;
- `ARCHITECTURE.md`;
- `DATA_MODEL.md`;
- `INVESTMENT_PHILOSOPHY.md`;
- `DESIGN_PRINCIPLES.md`;
- `DEVELOPMENT_GUIDELINES.md`;
- `ROADMAP.md`;
- Architecture Decision Records.

Code changes that alter documented behavior must update the relevant documentation.

---

# Article 20 — Architecture Decisions Must Be Recorded

Significant technical or product decisions must use an Architecture Decision Record.

An ADR should state:

- context;
- problem;
- decision;
- alternatives considered;
- consequences;
- risks;
- status;
- date.

Examples include:

- Python structures while AI interprets;
- confidence measures evidence quality;
- historical snapshots are immutable;
- review package is the primary Python-to-AI interface;
- no automatic trading;
- SQLite is used for structured historical queries.

---

# Article 21 — Long-Term Maintainability

Investment Terminal is a long-term product.

Development must prefer:

- readable code;
- explicit models;
- stable interfaces;
- small focused services;
- clear naming;
- limited hidden state;
- deterministic behavior;
- migration paths;
- backward compatibility;
- reviewable Git history.

Short-term speed must not create avoidable long-term fragility.

---

# Article 22 — Product Safety and Humility

The product must communicate uncertainty honestly.

It must not:

- guarantee returns;
- claim certainty;
- disguise missing context;
- exaggerate historical accuracy;
- treat correlation as causation;
- generalize from insufficient history;
- present backtests as guaranteed future performance;
- label evidence quality as success probability.

The system should prefer a cautious `WAIT` or `PARTIAL` conclusion over a falsely confident action.

---

# Article 23 — Definition of Done

A feature is complete only when applicable items are satisfied:

- the investment question is documented;
- the architecture location is clear;
- inputs and outputs are defined;
- business rules are documented;
- code is implemented;
- tests pass;
- warnings and partial states are supported;
- structured export is supported where relevant;
- history compatibility is considered;
- AI usability is considered;
- relevant documentation is updated;
- Git working tree is clean.

A feature that only “works locally” is not complete.

---

# Article 24 — Architecture Review

After approximately five to ten meaningful sprints, development should pause for an Architecture Review.

The review should assess:

- duplicated logic;
- domain boundaries;
- coupling;
- schema growth;
- naming consistency;
- technical debt;
- silent failures;
- confidence consistency;
- test quality;
- historical compatibility;
- documentation drift;
- opportunities to simplify.

The purpose is to keep the product understandable and reliable as it grows.

---

# Article 25 — Amendment Process

This Constitution may evolve, but it should not change casually.

An amendment requires:

1. a written proposal;
2. a clear reason;
3. analysis of affected modules and data contracts;
4. an ADR;
5. updated tests where behavior changes;
6. updated product documentation;
7. explicit acceptance.

Foundational statements such as the following require especially strong justification to change:

> Python structures. AI interprets. Humans decide.

> Confidence measures evidence quality, not future probability.

> History is immutable.

> Every recommendation must be explainable.

> Investment Terminal does not attempt to predict the future. It reduces uncertainty.
