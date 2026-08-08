# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 15 — Historical Outcome Methodology Hardening
planning
```

## Completed historical-intelligence foundation

### Sprint 12

- immutable historical Review Package archive;
- append-only manifest;
- SHA-256 integrity;
- History SQLite projection;
- verified package loading;
- typed imports;
- timeline foundation.

### Sprint 13

- historical query/navigation;
- schema migration foundation;
- explicit import state;
- snapshot compatibility;
- portfolio/holdings/recommendations/deployment comparison;
- aggregate comparison service;
- exact archived replay;
- normalized historical replay;
- read-only History CLIs;
- realistic History E2E fixture.

### Sprint 14

- canonical historical outcome models;
- `ELAPSED_DAYS` observation-window policy;
- historical recommendation transitions;
- recommendation-history service;
- exact local candle outcome-evidence adapter;
- raw close-price outcome calculator;
- explicit observation maturity/evidence states;
- on-demand outcome observation service;
- descriptive aggregation;
- outcome CLI;
- realistic outcome E2E fixture;
- no outcome persistence;
- History schema target remains version 2.

## Stable source-of-truth hierarchy

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

## Current limitation driving Sprint 15

Sprint 14 intentionally requires:

```text
ELAPSED_DAYS
+
exact timestamp candle match
```

This preserves correctness but is too narrow for realistic exchange-session observations.

The system currently has no canonical contract for:

- trading sessions;
- exchange holidays;
- session-aware endpoint selection;
- exact-vs-session evidence selection;
- methodology identity/version;
- deterministic fallback within an explicitly approved session policy.

Sprint 15 should solve those semantics before any effectiveness or confidence work.

## Sprint 15 objective

Introduce **session-aware and methodology-identifiable historical outcome observation** while preserving the evidence discipline established in Sprint 14.

The sprint should answer:

- What does “5 trading sessions later” mean?
- Which calendar/session source defines that endpoint?
- What happens if the exact endpoint has no candle?
- Which evidence-selection rule was used?
- Can two outcome observations be compared if their methodologies differ?
- Can the CLI expose methodology and evidence-selection semantics explicitly?

## Sprint 15 guardrails

Keep these stable:

- no hindsight leakage;
- no silent present-day fallback;
- no unbounded nearest-date substitution;
- no implicit exchange calendar;
- no network call inside pure outcome calculation;
- no outcome persistence unless separately justified;
- no success/failure scoring;
- no confidence calibration;
- no causal claims;
- no portfolio-performance wording for raw price movement;
- no schema v3 merely for convenience.

## Deferred capabilities

Not currently implemented:

- recommendation effectiveness scoring;
- hit rate;
- predictive confidence calibration;
- factor-effectiveness inference;
- total-return/dividend-adjusted outcomes;
- FX-adjusted outcomes;
- portfolio performance attribution;
- tax-lot performance;
- outcome persistence/materialization;
- current-code historical recalculation;
- Knowledge Domain;
- autonomous trading.

## Stable decisions

- immutable historical packages;
- append-only manifest;
- archived Review Package JSON remains canonical historical Review Package evidence;
- History SQLite remains a rebuildable projection;
- local candles are historical market evidence;
- outcome observations remain derived/on demand;
- recommendation transitions and market outcomes remain separate;
- raw close-price movement remains descriptive, not portfolio performance;
- CLI remains a composition/rendering boundary;
- History repositories own History persistence queries;
- History schema target remains version 2 until a real persistence requirement exists.
