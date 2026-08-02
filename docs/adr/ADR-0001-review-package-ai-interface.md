
# ADR-0001 — Review Package Is the Only AI Interface

**Status:** Accepted  
**Date:** 2026-08-02  
**Decision owner:** Investment Terminal Architecture  
**Scope:** Python engine, Review domain, History domain, AI interpretation layer  

---

## Context

Investment Terminal combines two fundamentally different types of work:

1. deterministic financial processing performed by the Python application;
2. contextual interpretation performed by an AI layer.

The Python engine is responsible for collecting, validating, normalizing,
calculating, structuring and preserving financial evidence.

The AI layer is responsible for interpreting structured evidence together with
current external context such as news, macroeconomics, monetary policy,
politics and geopolitics.

Without a stable boundary between these layers, the AI could become coupled to:

- internal Python classes;
- implementation-specific services;
- local database tables;
- temporary files;
- implicit application state;
- provider-specific formats.

Such coupling would reduce reproducibility, make historical analysis harder,
weaken schema governance and allow internal implementation changes to affect
the interpretation layer unpredictably.

Investment Terminal therefore requires one explicit, durable and
machine-readable interface between deterministic processing and AI-assisted
interpretation.

---

## Problem

How should structured evidence move from the deterministic Python engine to the
AI interpretation layer without exposing internal implementation details or
creating multiple competing interfaces?

The selected interface must support:

- reproducible analysis;
- historical archiving;
- schema versioning;
- backward compatibility;
- independent evolution of Python and AI;
- explicit missing-data and partial-result states;
- secure handling of personal portfolio information;
- future replay of historical reviews;
- one-file user workflows.

---

## Decision

The canonical interface between the Python engine and the AI interpretation
layer is:

```text
investment_review_package.json
```

The AI layer must consume the Investment Review Package rather than depend
directly on:

- internal Python classes;
- service objects;
- SQLite tables;
- provider clients;
- process memory;
- undocumented temporary exports;
- ad hoc combinations of unrelated files.

The approved interaction is:

```text
External and portfolio data
        ↓
Deterministic Python processing
        ↓
investment_review_package.json
        ↓
AI interpretation with current external context
        ↓
Human investment decision
```

All deterministic evidence intended for AI use must be exposed through the
Review Package or through a formally versioned companion artifact explicitly
referenced by the Review Package.

The Review Package is also the primary input to the immutable History domain.

---

## Decision Details

### 1. Python Owns Deterministic Facts

The Python engine remains responsible for:

- validated portfolio data;
- market and fundamental evidence;
- technical indicators;
- calculated rankings;
- machine recommendations;
- portfolio market values;
- policy gaps;
- contribution plans;
- deployment evidence;
- structured warnings;
- data freshness;
- evidence coverage;
- future confidence components;
- future decision traces.

The AI layer must not recreate these deterministic calculations when the
package already contains them.

### 2. AI Owns Interpretation

The AI layer may:

- explain relationships among package sections;
- combine package evidence with current news;
- add macroeconomic and geopolitical context;
- compare alternatives;
- identify conflicts;
- formulate scenarios;
- produce a user-facing investment review.

The AI layer must clearly distinguish:

- package-derived facts;
- externally researched facts;
- inference;
- judgment;
- uncertainty.

### 3. Human Owns the Final Decision

The Review Package and AI interpretation provide decision support only.

Neither layer automatically executes trades or replaces the user’s final
judgment.

### 4. New AI Requirements Extend the Contract

When the AI layer needs new deterministic evidence, the preferred process is:

```text
Investment question
        ↓
Data-model change
        ↓
Domain implementation
        ↓
Review Package extension
        ↓
Schema and compatibility tests
        ↓
AI consumption
```

Direct access to internal services is not an acceptable shortcut.

### 5. Historical Replay Is Required

A previously archived Review Package must remain analyzable by a later AI
version, subject to documented schema compatibility.

This allows:

- improved interpretation of old evidence;
- comparison of prior and current reasoning;
- evaluation of historical recommendations;
- recovery of the exact evidence available at decision time.

### 6. Internal Refactoring Must Not Break the AI Contract

The Python codebase may change its:

- service composition;
- internal models;
- provider implementations;
- database schemas;
- module organization.

These changes must not silently alter the meaning of the Review Package.

Breaking semantic changes require schema versioning and migration guidance.

---

## Review Package Requirements

The long-term Review Package contract must support:

- `schema_version`;
- unique package identity;
- generation timestamp;
- product version where available;
- explicit section statuses;
- source metadata;
- data-as-of timestamps;
- coverage information;
- structured issues;
- missing-context declarations;
- deterministic domain outputs;
- portfolio state;
- historical references when available.

A major section should eventually follow a consistent pattern similar to:

```json
{
  "status": "READY",
  "source": "PORTFOLIO_ENGINE",
  "generated_at": "2026-08-02T18:30:00+00:00",
  "data_as_of": "2026-08-01T20:00:00+00:00",
  "coverage": {
    "score": 1.0,
    "missing": []
  },
  "issues": [],
  "payload": {}
}
```

The exact package schema is defined separately in `DATA_MODEL.md` and future
schema specifications.

---

## Rationale

### Stable Separation of Responsibilities

A file-based contract creates a clear boundary:

- Python structures;
- AI interprets;
- humans decide.

### Reproducibility

The exact package can be saved and re-used.

The interpretation does not depend on transient process state.

### Historical Intelligence

The same artifact can be archived and normalized into structured history.

This makes the current review and historical record use the same evidence
boundary.

### Independent Evolution

Python and AI can evolve separately while respecting a versioned contract.

### Explainability

The final review can refer to explicit fields and sections rather than hidden
application state.

### Operational Simplicity

The user can generate one file and provide one file for analysis.

### Privacy Control

The user explicitly chooses when to share the package with an external AI
system.

---

## Alternatives Considered

### Alternative A — AI Reads the SQLite Database Directly

**Rejected.**

Problems:

- couples AI to internal database schema;
- makes migrations dangerous;
- exposes more private data than necessary;
- weakens section-level status and explanation;
- complicates historical replay;
- allows undocumented queries to alter interpretation.

SQLite remains an internal structured store, not the primary AI contract.

### Alternative B — AI Calls Python Services Directly

**Rejected.**

Problems:

- couples AI to runtime implementation;
- requires the application to be running;
- reduces portability;
- makes archived analysis difficult;
- makes reproducibility dependent on code version and environment.

### Alternative C — Multiple Files per Review

**Rejected as the primary workflow.**

Separate files for portfolio, quotes, fundamentals, rankings and recommendations
would:

- increase manual work;
- create synchronization risks;
- make completeness difficult to verify;
- complicate history and AI prompting.

Companion artifacts may exist for very large data, but must be explicitly
referenced by the canonical Review Package.

### Alternative D — AI Recalculates Everything from Raw Data

**Rejected.**

Problems:

- duplicates deterministic logic;
- creates inconsistent results;
- weakens tests;
- obscures which rules were used;
- makes historical reproduction unreliable.

### Alternative E — Human-Readable Report as the Main Interface

**Rejected.**

Markdown, PDF or Excel may be useful presentation formats, but they are not
sufficient as the canonical machine-readable contract.

---

## Positive Consequences

- one stable Python-to-AI boundary;
- reproducible reviews;
- simpler user workflow;
- easier immutable archiving;
- explicit schema governance;
- reduced coupling;
- improved privacy control;
- future compatibility with different AI systems;
- historical packages can be reinterpreted;
- deterministic facts remain separate from contextual judgment.

---

## Negative Consequences

- the Review Package may become large;
- schema design requires discipline;
- new AI requirements may require package changes;
- compatibility tests become mandatory;
- adapters are required between domain models and serialized output;
- poorly designed package sections could become a bottleneck.

These costs are accepted because a stable contract is more valuable than direct
runtime convenience.

---

## Risks

### Package Becomes a Monolithic Dump

Mitigation:

- domain-owned sections;
- explicit section contracts;
- adapters rather than arbitrary serialization;
- schema review;
- optional companion artifacts only when justified.

### Package Contains Stale or Partial Data

Mitigation:

- explicit freshness;
- coverage;
- section status;
- structured issues;
- confidence penalties.

### AI Treats Machine Signals as Final Decisions

Mitigation:

- explicit terminology;
- Recommendation is not Decision;
- final user responsibility;
- future ADR-0005.

### Sensitive Data Is Shared Unnecessarily

Mitigation:

- local generation;
- explicit user-controlled export;
- future redaction profiles;
- no credentials or secrets in the package.

---

## Compliance Rules

A change complies with this ADR when:

- deterministic AI-facing evidence is available in the Review Package;
- AI does not require direct access to internal Python state;
- the package clearly identifies partial or missing evidence;
- schema changes are tested and documented;
- archived packages remain interpretable;
- the AI layer does not modify canonical data.

A change violates this ADR when:

- an AI workflow depends on direct SQLite queries;
- internal classes become an undocumented AI API;
- multiple unversioned files replace the canonical package;
- package facts are silently recalculated by AI;
- breaking semantic changes occur without schema versioning.

---

## Implementation Status

| Area | Status |
|---|---|
| Review Package generation | Implemented |
| Portfolio section | Implemented |
| Machine recommendation sections | Implemented |
| Partial/fallback behavior | Partially implemented |
| Formal top-level schema version | To be strengthened |
| Immutable historical archive | Planned for Sprint 12 |
| Historical replay tests | Planned |
| Unified confidence section | Planned |
| Decision Trace section | Planned |
| Redaction profiles | Future |

---

## Related Documents

- `docs/PROJECT_VISION.md`
- `docs/CONSTITUTION.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/DESIGN_PRINCIPLES.md`
- `docs/QUALITY_ATTRIBUTES.md`
- `docs/DOMAIN_MAP.md`
- `docs/GLOSSARY.md`

---

## Future Evolution

This decision is expected to remain stable.

Future work may add:

- JSON Schema validation;
- package redaction profiles;
- package signatures or checksums;
- optional compressed packages;
- companion historical exports;
- evidence-reference graphs;
- package migration tools;
- AI response objects linked to package identity.

These additions must preserve the Review Package as the canonical boundary
between deterministic evidence and AI-assisted interpretation.
