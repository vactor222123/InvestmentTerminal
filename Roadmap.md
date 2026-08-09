# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 16 — Statistically Honest Outcome Research Foundation  
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

Sprint 16 implemented the research protocol that Sprint 15 deliberately required before any effectiveness or confidence scoring.

Delivered:

- canonical `HistoricalOutcomeResearchProtocol`;
- `DESCRIPTIVE_OUTCOME_RESEARCH@1`;
- explicit eligible observation policy;
- exact cohort grouping by methodology identity and observation-window semantics;
- visible coverage accounting for `COMPLETE / PARTIAL / UNAVAILABLE / NOT_MATURE`;
- explicit minimum eligible sample-size assessment;
- descriptive price-movement statistics;
- sample standard deviation and standard error;
- no invented confidence interval without an explicit interval policy;
- machine-readable descriptive-only claim boundary;
- protocol-aware research orchestration;
- population-selection metadata and archived-sample bias warnings;
- read-only research summary CLI;
- deterministic multi-observation E2E fixture;
- no research/outcome persistence;
- History schema remains version 2.

Canonical Sprint 16 research flow:

```text
methodology-aware observations
→ explicit research protocol
→ exact cohorts
→ eligibility + coverage
→ sample sufficiency
→ descriptive statistics
→ uncertainty
→ claim boundary
→ population metadata
→ read-only research result / CLI
```

Sprint 16 does **not** claim that positive historical price movement means a recommendation was successful or effective.

## 8. Stable Research Guardrails

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

## 9. Stable Historical Evidence Hierarchy

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Local market candle database
    persisted historical market-data evidence

Explicit local session calendar
    methodology input with provenance

Methodology-aware outcome observation
    rebuildable derived result

Protocol-aware research result
    rebuildable descriptive research result
```

Derived outcome and research results remain non-canonical and on demand.

## 10. Deferred Scope

Still deferred:

- recommendation success/failure labels;
- hit-rate/effectiveness scoring;
- predictive confidence calibration;
- inferential confidence intervals until an explicit interval policy exists;
- multiple-comparison inference;
- factor-effectiveness inference;
- causal attribution;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- portfolio performance attribution;
- tax-lot performance;
- outcome/research persistence or materialization;
- autonomous portfolio actions;
- broker execution;
- Knowledge Domain.

## 11. Next Product Decision Point

The next milestone should decide whether the historical evidence base and product requirements justify moving beyond descriptive research.

Any inferential or effectiveness-oriented milestone must first define its own versioned contracts for:

- target estimand;
- population assumptions;
- comparison/control semantics;
- interval/test methodology;
- multiple-comparison discipline;
- selection/survivorship treatment;
- methodology compatibility;
- causal vs non-causal wording.

The existence of Sprint 16 infrastructure alone is not permission to add a hit rate, effectiveness score, or predictive confidence.

## 12. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
