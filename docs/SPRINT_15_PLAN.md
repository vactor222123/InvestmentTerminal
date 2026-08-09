# Sprint 15 Plan — Historical Outcome Methodology Hardening

**Sprint:** 15  
**Status:** Implemented — final verification pending  
**Theme:** Historical Outcome Methodology Hardening  
**Depends on:** Sprint 14 — Outcome-Aware Historical Intelligence

---

# 1. Sprint Goal

Make historical outcome observation semantics realistic enough for exchange-traded instruments while preserving strict evidence provenance and deterministic reconstruction.

Sprint 14 established:

```text
ELAPSED_DAYS
+
exact timestamp price evidence
```

Sprint 15 added an explicit trading-session-aware methodology instead of weakening exact evidence with ad hoc fallback.

---

# 2. Delivered Architecture

```text
HistoricalRecommendationState
        +
HistoricalOutcomeMethodology
        ├─ window kind
        ├─ endpoint policy
        └─ evidence-selection policy
        +
explicit local session calendar
        ↓
endpoint resolution
        ↓
exact selected price evidence + provenance
        ↓
methodology-aware observation
        ↓
query/filter
        ↓
methodology-safe aggregation
        ↓
methodology-aware CLI
```

---

# 3. Delivered Tasks

## Task 1 — Methodology Identity Models — DONE

Delivered:

```text
HistoricalOutcomeMethodology
HistoricalEvidenceSelectionPolicy
HistoricalEndpointPolicy
```

Sprint 14 behavior is explicitly represented as:

```text
ELAPSED_DAYS_EXACT_CLOSE@1
```

## Task 2 — Market Session Models — DONE

Delivered:

```text
HistoricalMarketSession
HistoricalSessionCalendarIdentity
```

Includes session key/date, open/close timestamps, timezone, calendar identity, source/provenance, and deterministic ordering.

## Task 3 — Local Session Calendar Boundary — DONE

Delivered:

```text
HistoricalLocalSessionCalendar
```

Properties:

- read-only;
- deterministic;
- explicit sessions only;
- no weekday inference;
- no network access;
- no History persistence.

## Task 4 — Trading-Session Observation Window — DONE

Delivered:

```text
TRADING_SESSIONS
HistoricalTradingSessionWindowPolicy
HistoricalTradingSessionWindowResolution
```

Canonical v1:

```text
count explicit sessions where opens_at > origin_at
Nth session = endpoint session
endpoint_at = endpoint session closes_at
mature when as_of >= endpoint_at
```

## Task 5 — Evidence Selection Policy — DONE

Delivered exact-only policies:

```text
EXACT_TIMESTAMP_CLOSE@1
SESSION_CLOSE_EXACT@1
```

No generic nearest-date fallback exists.

## Task 6 — Methodology-Aware Price Evidence — DONE

Delivered:

```text
HistoricalMethodologyAwarePriceEvidence
HistoricalMethodologyAwarePriceEvidenceService
```

Output preserves methodology, intended endpoint, actual evidence timestamp, selection policy, price point, and optional session/calendar provenance.

## Task 7 — Methodology-Aware Observation Service — DONE

Delivered:

```text
HistoricalMethodologyAwareObservationService
HistoricalMethodologyAwareObservationResult
```

Origin evidence remains exact at the recommendation timestamp.

Endpoint evidence follows the explicit methodology.

Sprint 14 exact methodology remains supported.

## Task 8 — Methodology Compatibility Model — DONE

Delivered:

```text
COMPATIBLE
PARTIALLY_COMPATIBLE
INCOMPATIBLE
```

Compatibility is structural only and explicitly non-statistical.

## Task 9 — Outcome Query Filters — DONE

Delivered in-memory filters for:

- recommendation key;
- symbol;
- action;
- status;
- window kind/value;
- methodology ID/version;
- origin time range.

No persistence was added.

## Task 10 — Aggregation by Explicit Methodology — DONE

Delivered methodology-aware aggregation.

Rules:

```text
summarize_one
→ reject mixed methodology identities

summarize_grouped
→ separate exact methodology.identity_key groups
```

No effectiveness metric was added.

## Task 11 — Methodology-Aware CLI — DONE

Delivered a separate read-only methodology-aware CLI.

Supported methodologies:

```text
ELAPSED_DAYS_EXACT_CLOSE
TRADING_SESSIONS_EXACT_CLOSE
```

Session methodology requires an explicit local JSON session calendar.

CLI output exposes methodology, endpoint policy, evidence-selection policy, calendar provenance, window, coverage, and raw descriptive movement.

The Sprint 14 CLI remains unchanged.

## Task 12 — Realistic Session-Aware E2E Fixture — DONE

Delivered deterministic coverage for:

```text
Friday recommendation
→ explicit session calendar
→ weekend gap
→ Monday session close
→ exact session-close evidence
→ COMPLETE
→ raw outcome
→ methodology-aware aggregation
```

Additional coverage includes:

- `NOT_MATURE`;
- missing exact Monday close → `PARTIAL`;
- no nearest fallback;
- methodology/session/calendar provenance;
- JSON-ready output;
- no outcome table creation.

## Task 13 — Documentation and Sprint Review — IN PROGRESS

This package reconciles:

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/SPRINT_15_PLAN.md
docs/SPRINT_15_REVIEW.md
```

Final repository verification remains after applying this package.

---

# 4. Architecture Guardrails Preserved

Preserved:

- no hidden trading calendar;
- no hidden nearest-date lookup;
- explicit calendar source/provenance;
- explicit endpoint policy;
- explicit evidence-selection policy;
- deterministic session ordering;
- no network access in pure outcome logic;
- no current-price fallback;
- no History archive mutation;
- no outcome persistence;
- no schema v3;
- no success/effectiveness scoring;
- no confidence calibration;
- no causal claims;
- no portfolio-performance reinterpretation.

---

# 5. Backward Compatibility

Sprint 14 behavior remains explicitly supported:

```text
ELAPSED_DAYS_EXACT_CLOSE@1
```

Sprint 15 session-aware behavior is additive:

```text
TRADING_SESSIONS_EXACT_CLOSE@1
```

The original Sprint 14 CLI was intentionally left unchanged.

---

# 6. Persistence Decision

Final Sprint 15 decision:

```text
History schema target = 2
Outcome observations = on demand
Outcome aggregation = on demand
Session calendars = explicit local methodology input
```

No evidence emerged that justified History schema v3.

---

# 7. Explicit Non-Goals — PRESERVED

Sprint 15 did not implement:

- recommendation success/failure labels;
- hit rate;
- recommendation-effectiveness score;
- confidence calibration;
- factor-effectiveness scoring;
- causal inference;
- portfolio performance attribution;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- tax-lot outcomes;
- outcome persistence/materialization;
- autonomous trading;
- broker execution;
- Knowledge Domain.

---

# 8. Final Verification

After applying Task 13 docs:

```powershell
git diff --check
python -m pytest -q
git status --short
```

Sprint 15 is complete when:

- documentation diff is clean;
- full regression suite is green;
- `git status --short` is clean after commit;
- Task 13 docs are committed and pushed.

---

# 9. Next Milestone Recommendation

Do not jump directly to predictive confidence.

The next milestone should define a statistically honest effectiveness-research protocol:

- eligible historical samples;
- minimum sample sizes;
- exact methodology grouping;
- missing-evidence rules;
- observation-window policy;
- survivorship/selection-bias safeguards;
- uncertainty reporting;
- non-causal interpretation.

Only after those rules are explicit should the product decide whether to implement recommendation-effectiveness metrics.

---

# 10. Sprint Statement

> Sprint 14 taught Investment Terminal to observe what happened afterward. Sprint 15 made the meaning of “afterward” explicit for real market sessions while preserving exact evidence provenance and refusing hidden fallback.
