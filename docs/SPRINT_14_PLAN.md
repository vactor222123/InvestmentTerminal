# Sprint 14 Plan — Outcome-Aware Historical Intelligence

**Sprint:** 14  
**Status:** Completed  
**Theme:** Outcome-Aware Historical Intelligence  
**Depends on:** Sprint 13 — Historical Query, Comparison, and Replay Foundation  
**Closure baseline:** `develop @ 9107eaf`

---

# 1. Sprint Goal

Extend Historical Intelligence from “what changed?” to the first safe, evidence-grounded form of “what happened afterward?”

Sprint 14 introduced outcome semantics before outcome scoring.

The implemented system now provides explicit contracts for:

- elapsed-time observation windows;
- recommendation history and transitions;
- exact local historical price evidence;
- complete, partial, unavailable, and not-mature outcome observations;
- transparent raw close-price movement;
- descriptive aggregation with visible sample coverage;
- a read-only outcome CLI;
- deterministic end-to-end verification.

The implementation does not equate correlation with causation and does not claim that a recommendation caused a later market move.

---

# 2. Delivered Architecture

```text
Archived Review Package JSON
        ↓
History SQLite projection
        ↓
HistoricalRecommendationHistoryService
        ↓
HistoricalRecommendationState / Transition
        +
HistoricalObservationWindowPolicy
        +
HistoricalOutcomePriceEvidenceProvider
        ↓
HistoricalOutcomeObservationService
        ↓
HistoricalRecommendationOutcomeCalculator
        ↓
HistoricalOutcomeAggregator
        ↓
Read-only outcome CLI
```

Outcome observations remain derived, rebuildable, and on demand.

---

# 3. Canonical Sprint 14 Semantics

## Observation window

The first supported policy is:

```text
ELAPSED_DAYS
```

`N` means `N` absolute 24-hour periods from the recommendation snapshot `generated_at`.

The policy normalizes timestamps to UTC before endpoint calculation.

Sprint 14 does not implement trading-session windows, exchange calendars, weekend adjustment, holiday adjustment, or nearest-session substitution.

## Price evidence

Outcome price evidence is read from exact persisted local candles.

Required provenance includes:

- instrument/symbol;
- exact observation timestamp;
- close price;
- currency;
- candle resolution;
- source.

The source is explicitly identified as:

```text
LOCAL_CANDLE_REPOSITORY_CLOSE
```

No current quote fallback, network fetch, or nearest-date substitution is permitted.

## Observation statuses

Canonical statuses are:

```text
COMPLETE
PARTIAL
UNAVAILABLE
NOT_MATURE
```

`COMPLETE` requires exact origin and endpoint evidence suitable for the supported raw calculation.

`PARTIAL` preserves incomplete evidence or an unsupported same-observation calculation condition such as currency mismatch.

`UNAVAILABLE` represents an observation that cannot be evaluated from the required recommendation/evidence identity.

`NOT_MATURE` means the explicit endpoint has not yet been reached at the supplied `as_of`.

## Recommendation transitions

Historical recommendation transitions are factual and independent from price outcomes.

Supported transition types include:

```text
FIRST_OBSERVED
ACTION_CHANGED
METRICS_CHANGED
DESCRIPTIVE_CHANGED
DISAPPEARED
REAPPEARED
UNCHANGED
```

Stable recommendation keys and chronological snapshot ordering are required.

## Outcome calculation

The first supported descriptive metric is raw close-price movement:

```text
(endpoint_price / origin_price) - 1
```

The calculator does not interpret recommendation action and does not label an observation as success or failure.

Multi-currency FX-adjusted outcome calculation is not supported.

## Aggregation

Aggregation is in memory and read only.

It exposes:

- total observation count;
- complete count;
- partial count;
- unavailable count;
- not-mature count;
- complete-evidence coverage fraction;
- action counts;
- mean raw price-change fraction for `COMPLETE` observations;
- median raw price-change fraction for `COMPLETE` observations.

It does not expose success rate, hit rate, recommendation effectiveness, confidence calibration, portfolio performance, or causal attribution.

---

# 4. Task Closure

## Task 1 — Outcome Semantics and Models

**Completed.**

Delivered canonical immutable models for observation windows, evidence, and recommendation observations.

## Task 2 — Observation-Window Policy

**Completed.**

Selected `ELAPSED_DAYS` as the single Sprint 14 foundation.

No hidden market-calendar semantics were added.

## Task 3 — Historical Recommendation Transition Model

**Completed.**

Recommendation state and transition contracts cover first observation, action/metric/descriptive changes, disappearance, reappearance, and unchanged state.

## Task 4 — Recommendation History Repository / Service

**Completed.**

Historical recommendation state is exposed chronologically through typed History boundaries.

No raw SQL was moved into CLI.

## Task 5 — Outcome Price Evidence Boundary

**Completed.**

The implementation reuses the existing local `CandleRepository` through a read-only exact-price adapter.

No network or current-price fallback exists in this boundary.

## Task 6 — Single Recommendation Outcome Calculator

**Completed.**

Implemented transparent raw close-price movement with explicit evidence/currency requirements and no action interpretation.

## Task 7 — Outcome Observation Service

**Completed.**

The application service orchestrates recommendation state, window maturity, exact evidence, status selection, and optional calculation.

## Task 8 — Outcome Persistence Decision

**Completed.**

Decision:

```text
Outcome observations = rebuildable on-demand derived results
History schema target = 2
Schema v3 = deferred
```

See `docs/SPRINT_14_OUTCOME_PERSISTENCE_DECISION.md`.

## Task 9 — Outcome Query / Aggregation Models

**Completed.**

Added pure descriptive aggregation over already-produced observations.

## Task 10 — Outcome CLI

**Completed.**

Added a thin read-only CLI with human-readable and JSON output.

## Task 11 — Realistic Sprint 14 E2E Fixture

**Completed.**

The deterministic fixture covers:

```text
Review Packages
→ archive
→ manifest
→ History import
→ recommendation history
→ recommendation transition
→ exact local candles
→ mature / not-mature outcome observations
→ aggregation
→ CLI JSON
```

It also verifies that outcome analysis does not create an outcome table in History.

## Task 12 — Documentation and Sprint Review

**Completed by this documentation package, subject to final local regression and clean-tree verification.**

---

# 5. Persistence Decision

Sprint 14 does not persist outcome observations.

Source-of-truth hierarchy remains:

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Local candle database
    persisted historical market-data evidence

Outcome observation
    rebuildable derived result
```

No History schema version 3 is introduced.

Persistence may be reconsidered only after a concrete requirement establishes the need for caching, methodology audit snapshots, frozen research datasets, external evidence archiving, byte-stable derived-result reproducibility, or expensive large-scale materialization.

---

# 6. Explicit Non-Goals Preserved

Sprint 14 does not implement:

- portfolio performance attribution;
- cash-flow-adjusted returns;
- tax-lot outcomes;
- dividend-adjusted total return;
- FX-adjusted multi-currency return;
- success/failure scoring;
- recommendation effectiveness scoring;
- confidence calibration;
- factor-effectiveness inference;
- causal attribution;
- AI-generated historical conclusions;
- current-code historical recalculation;
- autonomous trading;
- broker execution;
- Knowledge Domain.

---

# 7. Definition of Done Reconciliation

Implemented and evidenced in repository code/tests:

- outcome terminology is canonical;
- observation-window semantics are explicit;
- recommendation transition history is queryable;
- price evidence carries explicit provenance;
- one transparent descriptive outcome calculation exists;
- incomplete and not-mature states are explicit;
- no current quote fallback is part of the outcome boundary;
- no network fetch is part of the outcome boundary;
- no portfolio-performance or causality metric is emitted;
- aggregation keeps sample counts and coverage visible;
- CLI remains a composition/rendering boundary;
- realistic deterministic E2E coverage exists;
- outcome persistence remains deferred and schema target remains 2.

Closure still requires the developer workstation checks:

```powershell
python -m pytest -q
git diff --check
git status --short
```

Sprint 14 is formally closed after those commands pass, the documentation commit is pushed, and the working tree is clean.

---

# 8. Sprint Statement

> Sprint 13 taught Investment Terminal what changed. Sprint 14 taught it how to observe what happened afterward — while keeping observation, performance, effectiveness, and causality separate.
