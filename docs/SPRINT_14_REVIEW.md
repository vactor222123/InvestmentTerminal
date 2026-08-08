# Sprint 14 Review — Outcome-Aware Historical Intelligence

**Sprint:** 14  
**Review baseline:** `develop @ 9107eaf`  
**Theme:** Outcome-Aware Historical Intelligence  
**Review status:** Implementation complete; final local regression / clean-tree verification required before formal closure.

---

# 1. Executive Summary

Sprint 14 successfully extends Historical Intelligence from historical comparison/replay into the first safe outcome-aware analysis layer.

The implementation can now observe what happened after a historical recommendation using:

- the historical recommendation state at a snapshot;
- an explicit elapsed-time observation window;
- exact local persisted candle evidence;
- explicit evidence/maturity statuses;
- a transparent raw close-price movement calculation;
- descriptive aggregation;
- a thin read-only CLI.

The sprint deliberately stops before recommendation effectiveness scoring, confidence calibration, portfolio-performance attribution, or causal inference.

This is the intended architectural boundary.

---

# 2. Delivered Flow

```text
Immutable archived Review Package
        ↓
History import / normalized projection
        ↓
Historical recommendation states
        ↓
Recommendation transitions
        +
Explicit ELAPSED_DAYS window
        +
Exact local candle evidence
        ↓
Historical outcome observation
        ↓
Raw close-price movement
        ↓
Descriptive aggregation
        ↓
Read-only outcome CLI
```

The realistic Sprint 14 E2E fixture verifies this flow without network access.

---

# 3. Task Review

## Task 1 — Outcome Semantics and Models

Delivered immutable contracts for:

```text
HistoricalObservationWindow
HistoricalOutcomeEvidence
HistoricalRecommendationObservation
```

Canonical observation statuses:

```text
COMPLETE
PARTIAL
UNAVAILABLE
NOT_MATURE
```

Evidence preserves price provenance including source, currency, and resolution.

**Assessment:** complete.

## Task 2 — Observation-Window Policy

The sprint selected one policy only:

```text
ELAPSED_DAYS
```

`N` means `N` absolute 24-hour periods from origin.

UTC normalization prevents local DST transitions from silently changing elapsed duration.

No market calendar is hidden inside the policy.

**Assessment:** complete.

## Task 3 — Historical Recommendation Transition Model

Recommendation state is modeled separately from market outcome.

Supported factual transition types include:

```text
FIRST_OBSERVED
ACTION_CHANGED
METRICS_CHANGED
DESCRIPTIVE_CHANGED
DISAPPEARED
REAPPEARED
UNCHANGED
```

**Assessment:** complete.

## Task 4 — Recommendation History Service

Historical recommendation states and transitions are available chronologically through typed History boundaries.

Stable recommendation keys are used; fuzzy identity is not introduced.

**Assessment:** complete.

## Task 5 — Outcome Price Evidence Boundary

The adapter uses the existing local `CandleRepository`.

It requires an exact timestamp match and returns explicit provenance.

It does not perform:

- network calls;
- current-price fallback;
- nearest-date fallback;
- naive timestamp coercion.

**Assessment:** complete.

## Task 6 — Single Recommendation Outcome Calculator

The first supported metric is:

```text
(endpoint_price / origin_price) - 1
```

It is intentionally a raw close-price movement metric.

The calculator does not inspect recommendation action and does not emit success/failure semantics.

Currency mismatch is not silently converted.

**Assessment:** complete.

## Task 7 — Outcome Observation Service

The service composes:

```text
recommendation state
+ window policy
+ exact price evidence
+ calculator
```

and returns an explicit observation plus an optional calculated outcome.

Maturity and evidence completeness remain visible.

**Assessment:** complete.

## Task 8 — Outcome Persistence Decision

Accepted decision:

```text
Outcome observations = rebuildable on-demand derived results
History schema target = 2
Schema v3 = deferred
```

This avoids premature duplication, invalidation rules, and methodology-versioning obligations.

**Assessment:** complete.

## Task 9 — Outcome Aggregation

The pure aggregator exposes:

- total count;
- status counts;
- complete-evidence coverage fraction;
- action counts;
- mean raw movement over complete observations;
- median raw movement over complete observations.

It does not expose:

- success rate;
- hit rate;
- recommendation effectiveness;
- confidence calibration;
- portfolio performance;
- causal scoring.

**Assessment:** complete.

## Task 10 — Outcome CLI

The read-only CLI accepts explicit:

```text
history database
market database
recommendation key
window days
as-of timestamp
candle resolution
```

It provides human-readable and JSON output.

Business logic remains in services/models rather than CLI.

**Assessment:** complete.

## Task 11 — Realistic E2E Fixture

The fixture uses realistic archived Review Packages and verifies:

```text
EM-ADD: BUY → HOLD
```

It covers:

- archive;
- manifest;
- History import;
- recommendation history;
- `ACTION_CHANGED`;
- exact local candle evidence;
- `COMPLETE`;
- `NOT_MATURE`;
- aggregation;
- CLI JSON;
- no outcome table in History.

**Assessment:** complete.

## Task 12 — Documentation / Closure

This review and the reconciled Sprint 14 plan/project status complete the documentation package.

Formal closure still depends on the final local commands listed below.

**Assessment:** ready for final verification.

---

# 4. Architectural Review

## Source-of-truth ownership

Sprint 14 preserves clear ownership:

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Local candle database
    historical price evidence

Outcome observation
    rebuildable derived result
```

No outcome table was added.

## Dependency direction

The approved dependency direction is preserved:

```text
CLI
 ↓
application services
 ↓
typed repositories / evidence adapters
 ↓
SQLite
```

Pure models/calculators do not fetch network data.

## Historical integrity

Outcome analysis does not mutate the archive.

The historical recommendation remains the recommendation that existed in the historical snapshot.

Later market evidence is attached as derived observation evidence rather than written back into the historical snapshot.

---

# 5. Safety of Interpretation

Sprint 14 keeps four concepts separate:

```text
historical recommendation
recommendation transition
later raw price movement
investment performance/effectiveness
```

Only the first three are represented.

Raw close-price movement is explicitly not:

- realized user return;
- portfolio return;
- recommendation success;
- causal impact;
- calibrated predictive accuracy.

This separation should remain a hard requirement in future sprints.

---

# 6. Known Limitations

The first outcome implementation intentionally has narrow semantics.

### Exact timestamp evidence

Price evidence requires an exact persisted candle timestamp.

There is no nearest trading session or market-calendar policy.

### Elapsed time only

Observation windows are absolute elapsed days, not trading days.

### Close price only

The metric uses persisted candle close prices.

No dividend/total-return adjustment exists.

### Same-currency calculation only

FX-adjusted multi-currency outcomes are not supported.

### On-demand reconstruction

Outcome observations are not persisted.

This is intentional until a concrete materialization/audit requirement exists.

### Descriptive aggregation only

Mean/median raw movement is not a recommendation-quality metric.

No minimum-sample effectiveness threshold has been approved.

---

# 7. Definition of Done Review

## Satisfied by implementation

- [x] outcome terminology is canonical;
- [x] observation-window semantics are explicit;
- [x] recommendation transition history is queryable;
- [x] price evidence has explicit provenance;
- [x] one descriptive outcome calculation is implemented;
- [x] incomplete/not-mature observations are explicit;
- [x] current quote fallback is prohibited;
- [x] network access is absent from pure outcome calculation/evidence lookup;
- [x] portfolio-performance overclaim is avoided;
- [x] causal overclaim is avoided;
- [x] architecture boundaries are explicit;
- [x] realistic deterministic E2E fixture exists;
- [x] outcome persistence decision is explicit;
- [x] documentation reconciliation is prepared.

## Must be verified locally before formal closure

- [ ] full regression suite passes;
- [ ] `git diff --check` passes;
- [ ] documentation commit is pushed;
- [ ] working tree is clean.

---

# 8. Final Verification Commands

Run from the repository root:

```powershell
python -m pytest -q
git diff --check
git status --short
```

After staging the documentation:

```powershell
git add docs/SPRINT_14_PLAN.md docs/PROJECT_STATUS.md docs/SPRINT_14_REVIEW.md
git diff --cached --check
git diff --cached --stat
```

Commit and push only if the checks are clean:

```powershell
git commit -m "docs(history): close sprint 14 outcome intelligence"
git push origin develop
git log -1 --oneline
git status --short
```

Expected final state:

```text
full pytest suite: PASS
git diff --check: no output
git diff --cached --check: no output before commit
git status --short: no output after commit/push
```

---

# 9. Sprint 15 Boundary

Sprint 15 should not automatically jump to confidence calibration.

The next plan should first decide which evidence question is valuable enough to justify the next complexity increase.

Candidate directions may include:

- explicit trading-session observation windows;
- methodology/version contracts for derived historical research;
- broader outcome query/filtering;
- carefully specified total-return evidence;
- sample-size policy before any recommendation-effectiveness analysis.

These are planning candidates, not Sprint 14 commitments.

---

# 10. Closure Statement

Sprint 14 establishes a safe outcome-aware Historical Intelligence foundation.

The system can now answer:

> What exact recommendation existed, what exact observation window was requested, what exact local price evidence exists at the origin and endpoint, and what raw close-price movement was observed?

It still refuses to silently turn that answer into:

> Therefore the recommendation was successful, caused the move, or produced the user’s investment return.

That distinction is the principal Sprint 14 outcome.
