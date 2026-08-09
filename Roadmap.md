# Investment Terminal вЂ” Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 18 вЂ” Explicit Historical Archive Continuity
**Current development branch:** `develop`

## 1. Product Evolution

```text
Foundation
в†’ Current-State Analysis
в†’ Portfolio and Decision Intelligence
в†’ Unified Review Package
в†’ Historical Intelligence Foundation
в†’ Historical Comparison and Replay
в†’ Outcome-Aware Historical Intelligence
в†’ Historical Outcome Methodology Hardening
в†’ Statistically Honest Outcome Research Foundation
в†’ Research Provenance and Population Quality Hardening
в†’ Explicit Historical Archive Continuity
в†’ Knowledge Domain
в†’ Evidence-Grounded AI Experience
```

## 2. Completed: Sprint 11

Architecture and canonical product documentation foundation.

## 3. Completed: Sprint 12 вЂ” Historical Intelligence Foundation

Delivered immutable Review Package history, integrity verification, History SQLite, typed imports, and timeline foundation.

## 4. Completed: Sprint 13 вЂ” Historical Comparison and Replay

Delivered historical navigation, comparison, compatibility, replay, read-only CLIs, schema migration foundation, and realistic History E2E coverage.

## 5. Completed: Sprint 14 вЂ” Outcome-Aware Historical Intelligence

Delivered canonical historical outcome observations, exact local price evidence, raw price-movement calculation, observation maturity/evidence states, descriptive aggregation, CLI, and E2E coverage.

Outcomes remained derived/on demand and History schema remained version 2.

## 6. Completed: Sprint 15 вЂ” Historical Outcome Methodology Hardening

Delivered explicit methodology identities, trading-session semantics, exact-only evidence selection, methodology-aware observations, query/filtering, methodology-safe aggregation, CLI, and deterministic session-aware E2E coverage.

Canonical methodologies remain:

```text
ELAPSED_DAYS_EXACT_CLOSE@1
TRADING_SESSIONS_EXACT_CLOSE@1
```

## 7. Completed: Sprint 16 вЂ” Statistically Honest Outcome Research Foundation

Delivered the explicit descriptive research protocol:

```text
DESCRIPTIVE_OUTCOME_RESEARCH@1
```

with exact cohorts, eligibility/coverage, sample sufficiency, descriptive statistics, uncertainty, claim boundaries, and population metadata.

## 8. Completed: Sprint 17 вЂ” Research Provenance and Population Quality Hardening

Delivered:

- explicit research population frame;
- non-exclusive query-selection accounting;
- temporal boundary completeness;
- source import-lifecycle quality;
- canonical four-component research provenance envelope;
- compatibility-safe migration;
- production-style provenance E2E.

Sprint 17 intentionally left internal archive continuity `NOT_ASSESSED` because no expected-cadence contract existed.

## 9. Completed: Sprint 18 вЂ” Explicit Historical Archive Continuity

Sprint 18 adds a versioned, opt-in expected archive cadence and exact continuity assessment without weakening Sprint 16/17 research guardrails.

Delivered:

- `FIXED_INTERVAL_ARCHIVE_CADENCE@1`;
- explicit `GENERATED_AT` timestamp basis;
- deterministic expected timestamp generation;
- exact expected-vs-observed gap assessment;
- canonical `COMPLETE / GAPS / NO_EXPECTATION` archive-gap statuses;
- repository-backed gap composition using `HistoricalSnapshotRepository`;
- internal continuity `NOT_ASSESSED / COMPLETE / GAPS`;
- strict separation between temporal boundary coverage and internal continuity;
- research-service wiring without persistence knowledge;
- opt-in CLI cadence arguments;
- real History SQLite continuity E2E;
- optional `ARCHIVE_GAP_ASSESSMENT` provenance extension;
- compatibility-safe preservation of the core `4/4` provenance denominator;
- JSON/human CLI contract coverage.

Canonical continuity flow:

```text
explicit cadence policy
в†’ expected GENERATED_AT grid
в†’ History SQLite snapshot timestamps
в†’ exact gap assessment
в†’ internal continuity
в†’ population completeness
в†’ optional archive-gap provenance
в†’ research CLI
```

The cadence contract is never inferred from observed history.

Version 1 does not model business days, exchange sessions, holidays, retries, or downtime.

## 10. Canonical Research Provenance

Core provenance remains:

```text
SOURCE_IMPORT_QUALITY
POPULATION_COMPLETENESS
POPULATION_FRAME
SELECTION_ACCOUNTING
```

Optional extension:

```text
ARCHIVE_GAP_ASSESSMENT
```

`complete_component_set = true` continues to mean only that all four core provenance components are available.

It does not mean:

```text
archive cadence was assessed
population is unbiased
population is representative
research is inferentially valid
recommendations are effective
```

## 11. Stable Research Guardrails

The following remain prohibited unless a future explicit methodology justifies them:

- success/failure labels;
- hit rate or win rate;
- recommendation-effectiveness scoring;
- predictive confidence calibration;
- causal inference;
- factor-effectiveness claims;
- portfolio-performance reinterpretation of raw price movement.

`SUFFICIENT` means only that the protocol minimum eligible sample size was met.

`COVERED` means only that observed source timestamps span the requested temporal boundaries.

`COMPLETE` internal continuity means only that all timestamps expected by the supplied cadence contract were observed in the assessed interval.

`COMPLETE` source import quality means only that all unique source snapshots have canonical `IMPORTED` lifecycle state.

None of these statuses establishes representativeness, predictive validity, causal validity, or recommendation effectiveness.

## 12. Stable Historical Evidence Hierarchy

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Historical import lifecycle
    source snapshot ingestion provenance

Explicit archive cadence
    runtime/versioned expectation contract

Archive gap assessment
    rebuildable continuity diagnostic

Local market candle database
    persisted historical market-data evidence

Explicit local session calendar
    methodology input with provenance

Methodology-aware outcome observation
    rebuildable derived result

Research provenance summary
    rebuildable source/population provenance

Protocol-aware research result
    rebuildable descriptive research result
```

Derived outcome, continuity, provenance, and research results remain non-canonical and on demand.

## 13. Deferred Scope

Still deferred:

- business-day/session/holiday-aware archive cadence;
- retry/downtime-aware cadence semantics;
- automatic cadence discovery;
- recommendation success/failure labels;
- hit-rate/effectiveness scoring;
- predictive confidence calibration;
- inferential confidence intervals;
- hypothesis-testing semantics;
- multiple-comparison inference;
- factor-effectiveness inference;
- causal attribution;
- market representativeness claims;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- portfolio performance attribution;
- tax-lot performance;
- outcome/research persistence or materialization;
- autonomous portfolio actions;
- broker execution;
- Knowledge Domain.

## 14. Next Product Decision Point

Sprint 18 closes the explicit archive-continuity hardening path.

The next milestone may proceed toward the deferred Knowledge Domain or define another explicit source/population contract.

Archive continuity must not be used as permission to introduce hit rate, effectiveness scores, predictive confidence, causal language, or implicit representativeness claims.

## 15. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
