# Sprint 14 Plan — Outcome-Aware Historical Intelligence

**Sprint:** 14  
**Status:** Planned  
**Theme:** Outcome-Aware Historical Intelligence  
**Depends on:** Sprint 13 — Historical Query, Comparison, and Replay Foundation

---

# 1. Sprint Goal

Extend Historical Intelligence from “what changed?” to the first safe, evidence-grounded form of “what happened afterward?”

Sprint 14 must introduce outcome semantics before outcome scoring.

The sprint should create explicit contracts for:

- observation windows;
- outcome evidence;
- recommendation transitions;
- price movement after historical signals;
- incomplete or unavailable outcome evidence;
- provenance and methodology.

The sprint must not equate correlation with causation and must not imply that a recommendation caused a later market move.

---

# 2. Product Questions

Sprint 14 should enable the system to answer:

- What recommendation existed at snapshot T0?
- Did the recommendation change before a selected observation window ended?
- What valid price evidence exists at T0 and at the observation endpoint?
- What simple price movement occurred over that explicitly defined interval?
- Is the outcome fully observed, partially observed, or unavailable?
- Which source and timestamp produced each outcome value?
- Can multiple recommendation observations be summarized without hiding sample size?

The sprint should **not** yet answer:

- Was the recommendation “correct” in a universal sense?
- Did the recommendation cause the later return?
- What would the user’s realized portfolio return have been?
- What is the calibrated probability of future success?

---

# 3. Architectural Baseline

Sprint 13 provides:

```text
HistoricalSnapshot
        ↓
Typed History repositories
        ↓
Timeline
        ↓
Compatibility
        ↓
SnapshotComparison
        ↓
Replay
```

Sprint 14 extends this carefully:

```text
Historical Recommendation Evidence
        +
Explicit Observation Window
        +
Explicit Price Evidence
        ↓
Outcome Observation
        ↓
Outcome Query / Aggregation
        ↓
Future Confidence Calibration
```

Outcome data must remain derived evidence, not a rewrite of the original snapshot.

---

# 4. Core Design Rules

1. Historical archive remains immutable canonical evidence.
2. Outcome calculations are derived and rebuildable.
3. Every observation window is explicit.
4. Every endpoint timestamp is explicit.
5. Price evidence must carry provenance.
6. Missing endpoint data remains missing.
7. No nearest-date substitution unless the policy is explicit and documented.
8. No present-day quote may silently stand in for a historical endpoint.
9. Recommendation transitions and price outcomes are separate concepts.
10. Simple price movement is not portfolio performance.
11. No outcome score without minimum-sample semantics.
12. No confidence calibration in the first package set.
13. CLI is added only after models/repositories/services exist.
14. All output ordering is deterministic.
15. No external-data fetch inside pure comparison/outcome models.

---

# 5. Explicit Non-Goals

Sprint 14 will not implement:

- portfolio performance attribution;
- cash-flow-adjusted portfolio returns;
- tax-lot outcomes;
- dividend-adjusted total return unless explicitly supported by evidence;
- FX-adjusted multi-currency return;
- current-code historical replay;
- AI-generated historical conclusions;
- causal attribution;
- autonomous trading;
- broker execution;
- Knowledge Domain;
- statistically calibrated recommendation confidence unless sample-size requirements are first approved.

---

# 6. Outcome Terminology

## Observation Origin

The historical point from which an outcome is evaluated.

Usually:

```text
recommendation snapshot generated_at
```

## Observation Window

An explicit interval after the origin.

Examples may eventually include:

```text
1 trading day
5 trading days
20 trading days
60 trading days
```

The final implementation must define whether windows are trading-session based or elapsed-time based. This decision must be explicit before calculations are added.

## Outcome Endpoint

The timestamp/session selected by the observation-window policy.

## Outcome Evidence

The source values used to calculate an observation, including:

- instrument identity;
- origin timestamp;
- endpoint timestamp;
- origin price;
- endpoint price;
- source/provenance;
- evidence status.

## Outcome Observation

A derived result describing what was observed after one historical recommendation.

It is not the historical recommendation itself.

## Recommendation Transition

A factual change in recommendation state across snapshots.

It is separate from market-price outcome.

---

# 7. Proposed Task Sequence

## Task 1 — Outcome Semantics and Models

### Goal

Define immutable contracts before calculating outcomes.

### Proposed models

```text
HistoricalObservationWindow
HistoricalOutcomeEvidence
HistoricalRecommendationObservation
```

### Required concepts

- explicit window kind;
- explicit window value;
- origin snapshot ID;
- stable recommendation key;
- symbol/instrument identity;
- recommendation action at origin;
- origin timestamp;
- endpoint timestamp;
- observation status;
- evidence provenance;
- warnings/limitations.

### Observation status candidates

```text
COMPLETE
PARTIAL
UNAVAILABLE
NOT_MATURE
```

The exact enum must be validated against the implementation needs before code is committed.

### Deliverables

```text
investment_terminal/history/historical_outcome_models.py
tests/test_historical_outcome_models.py
```

---

## Task 2 — Observation-Window Policy

### Goal

Define deterministic endpoint semantics.

### Required decisions

Choose and document one supported foundation:

- elapsed-time windows; or
- trading-session windows.

Do not implement both prematurely.

### Requirements

- timezone-aware;
- deterministic;
- no market-data access inside the value object/policy;
- explicit not-yet-mature handling;
- no hidden weekend/holiday assumptions.

### Deliverables

```text
investment_terminal/history/historical_observation_window.py
tests/test_historical_observation_window.py
```

---

## Task 3 — Historical Recommendation Transition Model

### Goal

Represent recommendation state across multiple snapshots without conflating it with price outcome.

### Detect

- first observed recommendation;
- action change;
- score/confidence movement;
- disappearance;
- reappearance;
- duration between observed states.

### Requirements

- stable recommendation key;
- chronological ordering;
- no fuzzy matching;
- no price calculations.

---

## Task 4 — Recommendation History Repository / Service

### Goal

Provide chronological recommendation observations through typed History boundaries.

### Requirements

- no raw SQL in CLI;
- stable deterministic ordering;
- snapshot/generated-at provenance;
- explicit missing history.

---

## Task 5 — Outcome Price Evidence Boundary

### Goal

Define how historical endpoint prices enter outcome analysis.

This task must audit existing market-history repositories before implementation.

### Required properties

- explicit source;
- explicit timestamp/session;
- instrument identity;
- no current quote fallback;
- missing evidence visible;
- no network call inside pure outcome calculation.

An adapter may use existing local historical-market infrastructure if architecture permits it after focused audit.

---

## Task 6 — Single Recommendation Outcome Calculator

### Goal

Calculate one descriptive outcome from explicit recommendation + price evidence.

### Initial metric

Prefer one simple transparent metric, for example raw price change:

```text
(endpoint_price / origin_price) - 1
```

Only after Task 5 establishes evidence semantics.

### Requirements

- no division by zero;
- no “success/failure” label by default;
- no portfolio-performance wording;
- no causal wording;
- explicit incomplete evidence behavior.

---

## Task 7 — Outcome Observation Service

### Goal

Orchestrate:

```text
Historical recommendation
+ observation window
+ explicit price evidence boundary
→ HistoricalRecommendationObservation
```

### Requirements

- application-service orchestration only;
- no raw SQL;
- no archive mutation;
- no hidden external context;
- deterministic output.

---

## Task 8 — Outcome Persistence Decision

### Goal

Decide whether Sprint 14 outcome observations should be:

- calculated on demand only; or
- persisted as a rebuildable derived projection.

Do not create a new table before this decision is justified.

If persistence is chosen, a new schema migration must be explicit.

---

## Task 9 — Outcome Query / Aggregation Models

### Goal

Provide descriptive aggregation without statistical overclaiming.

Potential fields:

- observation count;
- complete count;
- partial/unavailable count;
- action breakdown;
- median/mean movement only where mathematically justified;
- explicit sample size.

No confidence calibration yet.

---

## Task 10 — Outcome CLI

### Goal

Expose the approved outcome service through a thin read-only CLI.

CLI must be added only after service semantics stabilize.

---

## Task 11 — Realistic Sprint 14 E2E Fixture

### Required flow

```text
Historical Review Packages
→ imported History
→ recommendation history
→ explicit price evidence
→ observation window
→ outcome observation
→ query / CLI
```

Requirements:

- deterministic;
- no network;
- explicit timestamps;
- missing-data case;
- not-mature case;
- recommendation transition case.

---

## Task 12 — Documentation and Sprint 14 Review

Update canonical documentation only after implementation semantics are proven.

Create:

```text
docs/SPRINT_14_REVIEW.md
```

---

# 8. Architecture Guardrails

Allowed:

```text
Outcome Service
→ History repositories
→ explicit price-evidence adapter/repository
→ pure outcome calculator
```

Forbidden:

```text
Outcome model → network
Outcome comparator → raw SQL
CLI → outcome business rules
History archive → mutation
Outcome service → current quote fallback
Outcome calculation → causal claim
Outcome aggregation → hidden sample-size threshold
```

---

# 9. Data / Schema Strategy

Sprint 14 should **not assume schema version 3 is required**.

First determine whether outcome observations need persistence.

If persistence is justified:

- add an explicit migration;
- preserve schema-2 databases;
- keep outcome rows rebuildable;
- never move canonical evidence out of the archive;
- document ownership in History/Historical Intelligence.

---

# 10. Testing Strategy

Required categories:

- model validation;
- timezone validation;
- observation-window edge cases;
- immature window handling;
- missing price evidence;
- stable recommendation identity;
- transition ordering;
- zero-price protection;
- deterministic outcome calculation;
- provenance preservation;
- aggregation sample-size visibility;
- CLI JSON output if CLI is added;
- end-to-end fixture;
- architecture dependencies;
- full regression suite.

Commands:

```powershell
python -m pytest tests\<focused-test>.py -q
python -m pytest -q
```

---

# 11. Definition of Done

Sprint 14 is complete only when:

- outcome terminology is canonical;
- observation-window semantics are explicit;
- recommendation transition history is queryable;
- price outcome evidence has explicit provenance;
- at least one descriptive outcome calculation is implemented safely;
- incomplete/not-mature observations are explicit;
- no current-data leakage exists;
- no performance/causality overclaim exists;
- architecture boundaries are protected;
- realistic E2E tests pass;
- full regression tests pass;
- documentation is aligned;
- Sprint 14 review exists;
- working tree is clean;
- all changes are committed and pushed.

---

# 12. Recommended First Implementation Package

After this planning package, do **not** start with a repository or database migration.

Start with:

```text
Task 1 — Outcome Semantics and Models
```

Before writing that package, audit only:

- recommendation historical read model;
- recommendation comparator;
- timeline model;
- snapshot model;
- current market/historical price model conventions;
- Constitution/Data Model terminology.

The first code package should establish vocabulary and invariants without adding SQL or external data access.

---

# 13. Sprint Statement

> Sprint 13 taught Investment Terminal what changed. Sprint 14 will teach it how to observe what happened afterward — without pretending that observation is causation.
