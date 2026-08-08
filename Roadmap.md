# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 13 — Historical Comparison and Replay  
**Current development branch:** `develop`

## 1. Product Evolution

```text
Foundation
→ Current-State Analysis
→ Portfolio and Decision Intelligence
→ Unified Review Package
→ Historical Intelligence Foundation
→ Historical Comparison and Replay
→ Outcome Analysis and Confidence
→ Knowledge Domain
→ Evidence-Grounded AI Experience
```

## 2. Completed: Sprint 11

Architecture and canonical product documentation foundation.

## 3. Completed: Sprint 12 — Historical Intelligence Foundation

Delivered:

- `HistoricalSnapshot`;
- immutable Review Package archive;
- SHA-256 integrity;
- append-only manifest;
- archive CLI;
- SQLite history schema;
- snapshot repository;
- manifest synchronization;
- verified loader;
- summary/holdings/recommendations/deployment import;
- timeline builder;
- import pipeline;
- import CLI.

## 4. Completed Implementation: Sprint 13 — Historical Comparison and Replay

Sprint 13 extends History from preservation into safe historical intelligence.

Delivered capabilities:

### Query foundation

- canonical timeline event model;
- timeline repository;
- snapshot navigation queries.

### Schema evolution

- schema migration foundation;
- schema target version 2;
- explicit snapshot import-state table/model/repository;
- import-state workflow integration;
- legacy import-state reconciliation.

### Comparison foundation

- scalar and aggregate comparison models;
- comparison facts repository;
- snapshot compatibility service;
- portfolio-summary read model/repository/comparator;
- holdings read model/repository/comparator;
- recommendations read model/repository/comparator;
- deployment read model/repository/comparator;
- aggregate snapshot comparison service.

### Replay foundation

- replay request/result models;
- exact archived replay;
- normalized historical replay;
- explicit rejection of current-code recalculation.

### CLI

- History query CLI;
- snapshot comparison CLI;
- historical replay CLI.

### Integration quality

- deterministic realistic two-snapshot end-to-end fixture;
- archive → manifest → migration → sync → import → timeline → query → comparison → replay.

## 5. Sprint 13 Remaining Closure

- canonical documentation reconciliation;
- Sprint 13 architecture/review document;
- final Definition of Done verification.

## 6. Deferred Scope

Not part of Sprint 13:

- current-code historical recalculation;
- external-data replay;
- performance attribution;
- outcome analysis;
- recommendation effectiveness scoring;
- confidence calibration;
- Knowledge Domain;
- autonomous portfolio actions.

## 7. Next Product Direction

After Sprint 13 closure, the next logical layer is outcome-aware Historical Intelligence.

Candidate themes:

- historical recommendation outcome windows;
- signal duration;
- ranking movement;
- decision stability;
- evidence coverage over time;
- portfolio evolution;
- statistically honest confidence calibration.

These features must build on verified History rather than bypass it.

## 8. Long-Term Direction

The Knowledge Domain begins only after historical evidence volume and semantics are mature enough.

Knowledge must remain:

- evidence-linked;
- sample-size aware;
- versioned;
- rebuildable;
- separate from immutable historical facts.

## 9. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
