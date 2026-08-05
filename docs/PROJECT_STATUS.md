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
- checksum and schema validation;
- historical SQLite store;
- normalized historical import pipeline;
- historical timeline events;
- Sprint 12 architecture review;
- shared validation helpers;
- first atomic write infrastructure and JSON integrations.

## Sprint 13 progress

### Completed

- shared validation module;
- decision-model validation migration;
- historical snapshot validation migration;
- atomic write helper;
- atomic JSON writes for:
  - review-package export;
  - current portfolio replacement.

### In progress

- persistence failure-path coverage;
- final atomic-write integration review;
- transaction ownership;
- archive/manifest recovery behavior;
- architecture dependency tests;
- AI and engineering documentation.

### Next priorities

1. Add failure-path tests for atomic JSON integrations.
2. Clarify transaction ownership for historical imports.
3. Define archive/manifest partial-failure recovery.
4. Add dependency-direction tests.
5. Complete Sprint 13 documentation and changelog.

## Current quality baseline

The full suite contained 730 passing tests before the latest Sprint 13 atomic-write additions.

After every package:

```powershell
python -m pytest tests\<focused-test>.py -q
python -m pytest -q
```

The exact current count must be taken from the latest local run rather than hard-coded as a permanent project metric.

## Known architectural priorities

### Before the next feature-heavy sprint

- consistent timezone-aware persistence;
- safe mutable file writes;
- tested transaction rollback;
- explicit partial-failure recovery;
- protected dependency direction;
- documented schema-version ownership.

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
- deterministic ranking and recommendation ordering;
- frozen analytical result models;
- Review Domain as assembly boundary;
- CLI as composition boundary;
- archived JSON as historical source of truth.
