# Sprint 14 Outcome Persistence Decision

**Task:** 8 — Outcome Persistence Decision  
**Status:** Accepted  
**Decision:** Keep Sprint 14 outcome observations on demand; do not add History schema version 3 yet.  
**Reviewed baseline:** `develop @ 51686cf`

---

## 1. Decision

Historical outcome observations remain **derived on-demand results** in Sprint 14.

Do not add:

```text
historical_outcomes
recommendation_outcomes
outcome_observations
```

or any equivalent persisted table at this stage.

Do not change:

```text
HISTORICAL_SCHEMA_TARGET_VERSION = 2
```

for Task 8.

---

## 2. Why Persistence Is Not Required Yet

The current outcome result is deterministically reconstructible from already-owned inputs:

```text
Historical recommendation state
        +
HistoricalObservationWindow
        +
HistoricalObservationWindowPolicy
        +
Exact local historical candle evidence
        +
HistoricalRecommendationOutcomeCalculator
        ↓
HistoricalOutcomeObservationResult
```

No result currently contains unique source evidence that would be lost if the derived observation were not stored.

The canonical historical recommendation remains in History.

The local candle remains in the market database.

The window semantics and calculation methodology remain code/version contracts.

Therefore the current outcome result is a projection over existing facts, not a new canonical fact source.

---

## 3. Source-of-Truth Rule

Sprint 14 preserves the existing historical hierarchy:

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

Outcome observations do not become canonical historical evidence merely because they are useful.

---

## 4. Why Premature Persistence Would Be Risky

Persisting outcome rows now would create additional unresolved contracts.

### Methodology versioning

A persisted raw outcome would need to record which calculation/window methodology produced it.

### Invalidation

A persisted outcome could become stale if:

- historical candle evidence is corrected;
- provenance rules change;
- observation-window semantics change;
- calculation methodology changes;
- recommendation identity rules change.

### Duplication

The same derived fact would exist both as reconstructible inputs and as a stored output.

### Migration cost

A schema version 3 would become permanent compatibility surface without a demonstrated storage requirement.

### False authority

Persisted rows may be mistaken for original historical evidence rather than derived observations.

For Sprint 14, these costs outweigh the benefits.

---

## 5. Current Rebuild Contract

An outcome observation is rebuilt using explicit inputs:

```text
origin snapshot/recommendation key
window kind/value
as_of
price resolution
```

The result must preserve:

- origin snapshot identity;
- recommendation key;
- symbol/action at origin;
- origin and endpoint timestamps;
- observation status;
- price source;
- price currency;
- price resolution;
- raw prices;
- raw price change where complete;
- warnings/limitations.

No hidden current-data fallback is permitted.

---

## 6. Status Semantics Remain On Demand

Current observation states:

```text
COMPLETE
PARTIAL
UNAVAILABLE
NOT_MATURE
```

These states are inherently dependent on the explicit `as_of` value and available price evidence.

In particular, `NOT_MATURE` is time-relative.

Persisting it as a durable row would require a refresh/invalidation policy as time advances.

That is another reason not to persist Sprint 14 observations yet.

---

## 7. Criteria That Would Justify Persistence Later

Outcome persistence may be reconsidered only when at least one concrete requirement exists.

Examples:

### Expensive reconstruction

On-demand reconstruction is measurably too expensive for expected product usage.

### Methodology audit snapshots

The product must preserve the exact derived result produced under a specific historical methodology version.

### Batch outcome datasets

A later calibration/research workflow requires a frozen, versioned dataset of observations.

### External evidence ingestion

Outcome evidence begins to include externally retrieved historical data that must itself be archived with provenance/version identity.

### User-facing reproducibility contract

The product promises that a previously presented derived outcome can be reproduced byte-for-byte even after methodology changes.

### Large-scale aggregation

Repeated aggregation over many observations becomes operationally expensive enough to justify a materialized rebuildable projection.

None of these requirements is established in Task 8.

---

## 8. Requirements Before Any Future Schema v3

If persistence is later approved, the design must define before migration:

1. canonical row identity;
2. methodology version;
3. observation-window version;
4. price evidence provenance identity;
5. source candle identity or immutable evidence reference;
6. calculation timestamp;
7. invalidation/rebuild rules;
8. handling of corrected candle evidence;
9. uniqueness constraints;
10. whether `as_of` is part of identity;
11. which statuses are persistable;
12. whether persisted outcomes are cache, materialized projection, or audit artifact.

A schema migration must not precede these decisions.

---

## 9. Sprint 14 Architecture After This Decision

```text
History repositories
        ↓
HistoricalRecommendationHistoryService
        ↓
HistoricalRecommendationState
        +
HistoricalObservationWindowPolicy
        +
HistoricalOutcomePriceEvidenceProvider
        ↓
HistoricalOutcomeObservationService
        ↓
HistoricalRecommendationOutcomeCalculator
        ↓
On-demand result
```

No new History table is introduced.

---

## 10. Testing Consequence

Task 8 requires no new persistence/migration tests because no persistence surface changes.

Existing and future tests should instead verify:

- deterministic reconstruction;
- explicit `as_of`;
- exact price lookup;
- missing evidence;
- not-mature behavior;
- provenance preservation;
- no network/current-price fallback;
- no writes during outcome observation.

---

## 11. Decision Summary

**Accepted:**

```text
Outcome observations = rebuildable on-demand derived results
History schema target = 2
Schema v3 = deferred
```

This decision should remain in force until a concrete persistence requirement demonstrates that a new migration is worth the added lifecycle and invalidation complexity.
