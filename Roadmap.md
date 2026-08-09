# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 17 — Research Provenance and Population Quality Hardening  
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
→ Statistically Honest Outcome Research Foundation
→ Research Provenance and Population Quality Hardening
→ Knowledge Domain
→ Evidence-Grounded AI Experience
```

## 2. Completed: Sprint 11

Architecture and canonical product documentation foundation.

## 3. Completed: Sprint 12 — Historical Intelligence Foundation

Delivered immutable Review Package history, integrity verification, History SQLite, typed imports, and timeline foundation.

## 4. Completed: Sprint 13 — Historical Comparison and Replay

Delivered historical navigation, comparison, compatibility, replay, read-only CLIs, schema migration foundation, and realistic History E2E coverage.

## 5. Completed: Sprint 14 — Outcome-Aware Historical Intelligence

Delivered canonical historical outcome observations, exact local price evidence, raw price-movement calculation, observation maturity/evidence states, descriptive aggregation, CLI, and E2E coverage.

Outcomes remained derived/on demand and History schema remained version 2.

## 6. Completed: Sprint 15 — Historical Outcome Methodology Hardening

Delivered explicit methodology identities, trading-session semantics, exact-only evidence selection, methodology-aware observations, query/filtering, methodology-safe aggregation, CLI, and deterministic session-aware E2E coverage.

Canonical methodologies remain:

```text
ELAPSED_DAYS_EXACT_CLOSE@1
TRADING_SESSIONS_EXACT_CLOSE@1
```

## 7. Completed: Sprint 16 — Statistically Honest Outcome Research Foundation

Sprint 16 delivered the explicit descriptive research protocol required before any effectiveness or confidence scoring.

Canonical protocol:

```text
DESCRIPTIVE_OUTCOME_RESEARCH@1
```

It established:

```text
methodology-aware observations
→ exact cohorts
→ eligibility + coverage
→ sample sufficiency
→ descriptive statistics
→ uncertainty
→ claim boundary
→ population metadata
```

Sprint 16 did not claim that positive historical price movement means a recommendation was successful or effective.

## 8. Completed: Sprint 17 — Research Provenance and Population Quality Hardening

Sprint 17 strengthened the evidence/population boundary around Sprint 16 research without introducing new inferential or effectiveness semantics.

Delivered:

- explicit research population frame with pre-selection and post-selection denominators;
- query-selection provenance integrated into the research result;
- CLI visibility for produced/source, selected, excluded, and eligible populations;
- non-exclusive selection-reason accounting for recommendation, symbol, action, status, window, methodology, and origin-time filters;
- canonical source temporal-boundary completeness assessment;
- explicit `UNKNOWN / PARTIAL / COVERED` completeness semantics;
- explicit `NOT_ASSESSED` internal continuity when no canonical archive cadence exists;
- source import-lifecycle quality assessment based on unique origin snapshots;
- explicit `COMPLETE / PARTIAL / UNKNOWN` import-quality semantics;
- canonical `HistoricalOutcomeResearchProvenanceSummary`;
- one provenance envelope for import quality, temporal completeness, population frame, and selection accounting;
- compatibility-safe Python and serialization migration for pre-provenance callers;
- production-style provenance E2E using History SQLite and local market SQLite;
- no new research persistence;
- History schema remains version 2.

Canonical Sprint 17 provenance flow:

```text
source snapshots
→ import lifecycle quality
→ methodology-aware source observations
→ temporal completeness
→ population frame
→ selection accounting
→ selected candidates
→ eligibility + coverage
→ descriptive research result
→ provenance envelope
```

The canonical provenance envelope contains:

```text
SOURCE_IMPORT_QUALITY
POPULATION_COMPLETENESS
POPULATION_FRAME
SELECTION_ACCOUNTING
```

`complete_component_set = true` means only that all provenance components are available. It does not mean the population is unbiased, representative, causally valid, or suitable for inferential claims.

## 9. Stable Research Guardrails

The following remain prohibited unless a future explicit methodology justifies them:

- success/failure labels;
- hit rate or win rate;
- recommendation-effectiveness scoring;
- predictive confidence calibration;
- causal inference;
- factor-effectiveness claims;
- portfolio-performance reinterpretation of raw price movement.

`SUFFICIENT` means only that the protocol's minimum eligible sample size was met.

It does not mean:

```text
statistically significant
predictive
causal
effective
representative of the market
```

`COVERED` means only that observed source timestamps span the explicitly requested temporal boundaries.

It does not establish internal archive continuity.

`COMPLETE` source import quality means only that all unique source snapshots have canonical `IMPORTED` lifecycle state.

It does not establish population representativeness.

## 10. Stable Historical Evidence Hierarchy

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Historical import lifecycle
    source snapshot ingestion provenance

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

Derived outcome, provenance, and research results remain non-canonical and on demand.

## 11. Deferred Scope

Still deferred:

- recommendation success/failure labels;
- hit-rate/effectiveness scoring;
- predictive confidence calibration;
- inferential confidence intervals until an explicit interval policy exists;
- hypothesis-testing semantics;
- multiple-comparison inference;
- factor-effectiveness inference;
- causal attribution;
- archive-continuity claims without an explicit expected-cadence contract;
- market representativeness claims;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- portfolio performance attribution;
- tax-lot performance;
- outcome/research persistence or materialization;
- autonomous portfolio actions;
- broker execution;
- Knowledge Domain.

## 12. Next Product Decision Point

Sprint 17 closes the descriptive evidence/population hardening path proposed after Sprint 16.

A future milestone may choose one of two directions:

1. remain descriptive and improve archive/source contracts further, such as explicit expected archive cadence or population-universe definition; or
2. define a new versioned inferential/comparative protocol.

Any inferential or effectiveness-oriented milestone must first define its own contracts for:

- target estimand;
- source and target population assumptions;
- comparison/control semantics;
- interval/test methodology;
- multiple-comparison discipline;
- selection/survivorship treatment;
- methodology compatibility;
- causal vs non-causal wording.

Sprint 17 provenance infrastructure is not permission to add hit rate, effectiveness scores, predictive confidence, or causal language.

## 13. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
