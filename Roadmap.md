# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 15 — Historical Outcome Methodology Hardening  
**Current development branch:** `develop`

## 1. Product Evolution

```text
Foundation
→ Current-State Analysis
→ Portfolio and Decision Intelligence
→ Unified Review Package
→ Historical Intelligence Foundation
→ Historical Comparison and Replay
→ Outcome-Aware Historical Intelligence
→ Historical Outcome Methodology Hardening
→ Statistically Honest Effectiveness Research
→ Knowledge Domain
→ Evidence-Grounded AI Experience
```

## 2. Completed: Sprint 11

Architecture and canonical product documentation foundation.

## 3. Completed: Sprint 12 — Historical Intelligence Foundation

Delivered:

- immutable Review Package archive;
- SHA-256 integrity;
- append-only manifest;
- History SQLite foundation;
- verified historical package loader;
- typed historical imports;
- timeline foundation.

## 4. Completed: Sprint 13 — Historical Comparison and Replay

Delivered:

- timeline queries and navigation;
- schema migrations and explicit import state;
- typed historical comparison;
- compatibility assessment;
- exact archived replay;
- normalized historical replay;
- read-only query/comparison/replay CLIs;
- deterministic realistic History E2E coverage.

## 5. Completed: Sprint 14 — Outcome-Aware Historical Intelligence

Delivered:

- canonical outcome models;
- `ELAPSED_DAYS` observation-window semantics;
- historical recommendation state and transition analysis;
- chronological recommendation history;
- exact local candle price-evidence boundary;
- raw descriptive price-movement calculation;
- `COMPLETE / PARTIAL / UNAVAILABLE / NOT_MATURE` observation status;
- descriptive in-memory aggregation;
- read-only outcome CLI;
- deterministic realistic outcome E2E fixture;
- outcomes remain on demand;
- History schema remains version 2.

Sprint 14 deliberately did not implement recommendation-effectiveness scoring or confidence calibration.

## 6. Completed: Sprint 15 — Historical Outcome Methodology Hardening

Delivered:

- immutable outcome methodology identity/version contracts;
- explicit endpoint-policy and evidence-selection-policy identities;
- explicit market-session and session-calendar models;
- deterministic local read-only session-calendar boundary;
- `TRADING_SESSIONS` observation-window semantics;
- session-close endpoint resolution;
- exact-only `EXACT_TIMESTAMP_CLOSE@1`;
- exact-only `SESSION_CLOSE_EXACT@1`;
- methodology-aware price-evidence provenance;
- methodology-aware outcome observation orchestration;
- structural methodology compatibility assessment;
- read-only outcome query filters;
- methodology-safe descriptive aggregation;
- methodology-aware CLI;
- deterministic Friday → weekend → Monday session-aware E2E coverage;
- explicit preservation of Sprint 14 `ELAPSED_DAYS_EXACT_CLOSE@1`;
- no outcome persistence;
- History schema remains version 2.

Sprint 15 deliberately did not add generic nearest-date fallback, success labels, effectiveness scoring, predictive confidence, causal inference, or portfolio-performance attribution.

## 7. Current Product Decision Point

The system now has sufficiently explicit historical outcome methodology to begin designing a **statistically honest effectiveness research protocol**.

The next milestone should not immediately introduce a confidence model.

It should first define:

- research population and eligible historical observations;
- exact methodology grouping rules;
- minimum sample sizes;
- treatment of `PARTIAL`, `UNAVAILABLE`, and `NOT_MATURE`;
- multiple observation-window handling;
- methodology-version comparability;
- symbol/action grouping rules;
- survivorship and selection-bias safeguards;
- uncertainty and interval reporting;
- descriptive-vs-inferential metric boundaries;
- explicit non-causal interpretation.

Only after those contracts are stable should recommendation-effectiveness metrics be considered.

## 8. Deferred Scope

Still deferred:

- recommendation success/failure labels;
- hit-rate/effectiveness scoring;
- predictive confidence calibration;
- factor-effectiveness inference;
- causal attribution;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- portfolio performance attribution;
- tax-lot performance;
- outcome persistence/materialization;
- autonomous portfolio actions;
- broker execution;
- Knowledge Domain.

## 9. Stable Historical Evidence Hierarchy

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Local market candle database
    persisted historical market-data evidence

Explicit local session calendar
    session/calendar evidence supplied to methodology

Outcome observation
    rebuildable derived result

Outcome aggregation
    rebuildable descriptive summary grouped by exact methodology
```

## 10. Knowledge Domain Boundary

The Knowledge Domain begins only after historical evidence volume, methodology, and research semantics are mature enough.

Knowledge must remain:

- evidence-linked;
- sample-size aware;
- methodology-version aware;
- rebuildable;
- uncertainty aware;
- separate from immutable historical facts.

## 11. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
