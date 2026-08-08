# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 14 — Outcome-Aware Historical Intelligence  
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
- explicit decision to keep outcomes on demand and History schema at version 2.

Sprint 14 deliberately did not implement recommendation-effectiveness scoring or confidence calibration.

## 6. Current: Sprint 15 — Historical Outcome Methodology Hardening

Sprint 15 should make outcome observation semantics realistic enough for exchange-traded instruments without weakening evidence discipline.

Primary themes:

- explicit trading-session observation windows;
- explicit endpoint/evidence selection policy;
- market-session/calendar boundary;
- methodology identity/version contracts;
- deterministic session-aware local evidence lookup;
- broader read-only outcome querying/filtering;
- methodology-aware CLI output;
- realistic E2E coverage across weekends/holidays/session gaps.

Sprint 15 should not introduce predictive confidence or success scoring.

## 7. Deferred Scope

Not part of Sprint 15 unless explicitly re-approved after methodology work:

- recommendation success/failure labels;
- hit-rate/effectiveness scoring;
- confidence calibration;
- factor-effectiveness inference;
- causal attribution;
- portfolio performance attribution;
- tax-lot performance;
- autonomous portfolio actions;
- Knowledge Domain.

## 8. Next Product Direction

After Sprint 15, the next decision should be whether the available historical sample and methodology quality are sufficient for **statistically honest effectiveness research**.

Before any confidence model, define:

- minimum sample sizes;
- grouping dimensions;
- survivorship rules;
- missing-evidence treatment;
- multiple-window handling;
- methodology-version comparability;
- uncertainty reporting;
- explicit non-causal interpretation.

## 9. Knowledge Domain Boundary

The Knowledge Domain begins only after historical evidence volume and semantics are mature enough.

Knowledge must remain:

- evidence-linked;
- sample-size aware;
- methodology-version aware;
- rebuildable;
- separate from immutable historical facts.

## 10. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
