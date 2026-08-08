# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 13 — Architecture Stabilization
```

## Completed foundations

- portfolio modelling and current portfolio workflows;
- market-data clients, repositories, freshness and refresh services;
- technical indicators and scoring;
- fundamental analysis and data-quality handling;
- decision engine;
- ranking and recommendation flows;
- contribution and deployment planning;
- unified Review Package;
- immutable historical review archive;
- append-only snapshot manifest;
- checksum, path-safety, encoding, schema and timestamp identity validation;
- historical SQLite store;
- normalized historical import pipeline;
- historical timeline events;
- Sprint 12 architecture review;
- shared validation helpers;
- atomic write infrastructure and JSON integrations;
- atomic historical detail import;
- unified verified historical byte reads;
- History query boundary for CLI and import pipeline.

## Sprint 13 progress

### Completed

- shared validation module;
- decision-model validation migration;
- historical snapshot validation migration;
- atomic write helper;
- atomic JSON writes for:
  - review-package export;
  - current portfolio replacement;
- historical detail import transaction ownership;
- rollback-safe retry after failed detail import;
- archive-root confinement for historical integrity verification;
- read-once verified historical byte contract;
- History query ownership moved behind `HistoricalSnapshotRepository`;
- direct History SQLite queries removed from `import_history.py`.

### In progress

- persistence failure-path coverage;
- archive/manifest recovery behavior;
- architecture dependency tests;
- governance and engineering documentation;
- broader Sprint 13 historical query/comparison/replay work.

### Next priorities

1. Complete governance/status reconciliation after History hardening.
2. Add remaining dependency-direction tests.
3. Continue public History query and timeline interfaces from the Sprint 13 plan.
4. Define explicit import-state evolution only when required by the broader Sprint 13 design.
5. Continue snapshot comparison and replay foundations without weakening immutable evidence rules.

## Current quality baseline

The exact current passing-test count must be taken from the latest local run rather than hard-coded as a permanent project metric.

After every package:

```powershell
python -m pytest tests\<focused-test>.py -q
python -m pytest -q
```

## Known architectural priorities

### Before the next feature-heavy sprint

- consistent timezone-aware persistence;
- safe mutable file writes;
- tested transaction rollback;
- explicit partial-failure recovery where transactions cannot provide atomicity;
- protected dependency direction;
- documented schema-version ownership;
- rebuildable History projections from immutable archive evidence.

### Improve incrementally

- repository protocols;
- typed domain classifications;
- structured exception hierarchy;
- explicit configuration injection;
- database migrations;
- consolidated serialization helpers only where proven useful.

## Stable decisions

Keep these unless requirements change:

- immutable historical packages;
- append-only manifest;
- SHA-256 verification;
- exclusive archive creation;
- verified bytes are the exact bytes later decoded and parsed;
- deterministic ranking and recommendation ordering;
- frozen analytical result models;
- Review Domain as assembly boundary;
- CLI as composition boundary;
- archived JSON as historical source of truth;
- SQLite as a rebuildable structured History projection;
- History-domain repositories own History persistence queries.
