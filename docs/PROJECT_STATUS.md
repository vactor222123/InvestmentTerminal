# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 14 — Outcome-Aware Historical Intelligence
closure review
```

## Completed foundations

- portfolio modelling and current portfolio workflows;
- market-data clients, repositories, freshness and refresh services;
- technical and fundamental analysis;
- decision, ranking, and recommendation flows;
- contribution and deployment planning;
- unified Review Package;
- immutable historical Review Package archive;
- append-only snapshot manifest;
- checksum, path-safety, encoding, schema, and timestamp identity validation;
- History SQLite schema with controlled migrations;
- explicit historical import state;
- atomic historical detail import;
- read-once verified historical byte contract;
- typed History repositories;
- historical timeline models and queries;
- snapshot navigation;
- snapshot compatibility assessment;
- portfolio-summary comparison;
- holdings comparison;
- recommendations comparison;
- deployment comparison;
- aggregate snapshot comparison;
- exact archived replay;
- normalized historical replay;
- read-only History query/comparison/replay CLIs;
- realistic deterministic History end-to-end fixture;
- Sprint 13 architecture and Definition-of-Done review;
- canonical historical outcome models;
- elapsed-day observation-window policy;
- historical recommendation state and transition analysis;
- chronological recommendation-history service;
- exact local candle outcome-evidence boundary;
- raw descriptive historical price-movement calculator;
- outcome observation orchestration with explicit maturity/evidence status;
- explicit decision to keep outcomes on demand and History schema at version 2;
- descriptive outcome aggregation with visible coverage/sample counts;
- read-only historical outcome CLI;
- realistic deterministic Sprint 14 outcome end-to-end fixture.

## Sprint 13 closure

Sprint 13 is formally closed.

Stable historical source-of-truth rule:

```text
Archived Review Package JSON = canonical historical evidence
manifest.jsonl               = append-only index
history.db                   = rebuildable projection
```

## Sprint 14 delivered capability

Sprint 14 adds the first outcome-aware Historical Intelligence layer.

Implemented flow:

```text
Historical recommendation evidence
        +
Explicit elapsed-time window
        +
Exact local historical close-price evidence
        ↓
Outcome observation
        ↓
Raw descriptive price movement
        ↓
Descriptive aggregation
        ↓
Read-only CLI
```

The system can now answer:

- what recommendation existed at a historical snapshot;
- how that recommendation changed across snapshots;
- whether an explicit outcome window has matured;
- whether exact origin/endpoint price evidence exists;
- what raw close-price movement occurred over a complete observation;
- how many observations are complete, partial, unavailable, or not mature;
- which action counts and descriptive raw-movement summaries exist for complete observations.

The system still does **not** claim:

- that a recommendation caused a later price move;
- that raw price movement is portfolio performance;
- that a recommendation was universally correct or incorrect;
- that historical outcomes calibrate future confidence;
- that a small historical sample establishes effectiveness.

## Sprint 14 canonical semantics

### Observation window

Sprint 14 supports:

```text
ELAPSED_DAYS
```

The endpoint is `N` absolute 24-hour periods after origin, calculated in UTC.

Trading-session calendars and nearest-session substitution are not supported.

### Outcome evidence

Price evidence comes from exact local persisted candles.

No current quote fallback, network fetch, or nearest-date substitution is allowed.

Evidence preserves timestamp, source, currency, and resolution provenance.

### Observation status

```text
COMPLETE
PARTIAL
UNAVAILABLE
NOT_MATURE
```

### Outcome metric

```text
(endpoint_price / origin_price) - 1
```

This is raw close-price movement only.

### Aggregation

Aggregation exposes counts, complete-evidence coverage, action breakdown, and mean/median raw movement over `COMPLETE` observations only.

It does not expose success rate, hit rate, recommendation effectiveness, confidence calibration, or causal scoring.

## Sprint 14 persistence decision

Outcome observations remain on-demand derived results.

```text
History schema target = 2
Schema v3 = deferred
```

Current source-of-truth hierarchy:

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

## Current architectural baseline

### History

History repositories own History persistence queries.

The immutable archive remains canonical historical Review Package evidence.

### Historical Intelligence

Historical Intelligence owns relationships and derived analysis across historical evidence:

```text
timeline
comparison
replay
recommendation transitions
outcome observations
descriptive outcome aggregation
```

### Market evidence

Historical outcome price evidence uses exact local candles through the existing candle repository boundary.

It does not fetch network data.

### CLI

CLI remains a composition/rendering boundary.

The outcome CLI composes typed History repositories, the recommendation-history service, window policy, price-evidence adapter, observation service, calculator, and aggregator.

Outcome business rules remain outside CLI.

## Quality baseline

After each logical package:

```powershell
python -m pytest tests\<focused-test>.py -q
python -m pytest -q
```

The passing-test count is intentionally not hard-coded as a permanent project metric.

Before Sprint 14 is formally closed, run:

```powershell
python -m pytest -q
git diff --check
git status --short
```

## Sprint 14 closure status

Implementation Tasks 1–11 are complete.

Task 12 documentation reconciliation is prepared.

Formal closure requires:

1. full regression suite passes;
2. documentation diff check passes;
3. documentation changes are committed and pushed;
4. working tree is clean.

After those checks, Sprint 14 is formally closed and Sprint 15 planning may begin.

## Deferred capabilities

Not currently implemented:

- trading-session outcome windows;
- market-calendar-aware endpoint selection;
- nearest-session price substitution;
- dividend-adjusted total-return outcomes;
- FX-adjusted multi-currency outcomes;
- outcome persistence/materialization;
- current-code historical recalculation;
- external-context historical replay;
- portfolio performance attribution;
- tax-lot performance;
- recommendation effectiveness scoring;
- success/hit-rate scoring;
- confidence calibration from historical outcomes;
- factor-effectiveness inference;
- Knowledge Domain;
- autonomous trading.

## Stable decisions

Keep these unless requirements materially change:

- immutable historical packages;
- append-only manifest;
- SHA-256 verification;
- exclusive archive creation;
- verified bytes are the bytes later decoded and parsed;
- timezone-aware persisted timestamps;
- stable-key historical identity;
- deterministic ordering;
- Review Domain as assembly boundary;
- History Domain as evidence/persistence boundary;
- Historical Intelligence as relationship-analysis boundary;
- CLI as composition boundary;
- archived JSON as historical Review Package source of truth;
- SQLite History as a rebuildable projection;
- local persisted candles as Sprint 14 historical price evidence;
- exact timestamp matching for Sprint 14 outcome evidence;
- elapsed-day observation windows as the first supported policy;
- raw close-price movement is descriptive evidence, not portfolio performance;
- recommendation transitions and price outcomes remain separate;
- outcome observations remain on demand;
- History schema target remains version 2 until persistence is justified.
