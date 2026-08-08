# Sprint 15 Plan — Historical Outcome Methodology Hardening

**Sprint:** 15  
**Status:** Planned  
**Theme:** Historical Outcome Methodology Hardening  
**Depends on:** Sprint 14 — Outcome-Aware Historical Intelligence

---

# 1. Sprint Goal

Make historical outcome observation semantics realistic enough for exchange-traded instruments while preserving strict evidence provenance and deterministic reconstruction.

Sprint 14 established a safe first outcome model using:

```text
ELAPSED_DAYS
+
exact timestamp price evidence
```

Sprint 15 should add explicit **trading-session-aware methodology** rather than weakening the exact-evidence contract with ad hoc fallback rules.

The sprint should introduce:

- a market-session/calendar boundary;
- trading-session observation windows;
- explicit endpoint-resolution semantics;
- explicit evidence-selection semantics;
- methodology identity/version;
- methodology-aware observation output;
- broader read-only outcome querying/filtering;
- deterministic E2E coverage for weekends/session gaps.

---

# 2. Product Questions

Sprint 15 should enable the system to answer:

- What is the fifth trading session after a historical recommendation?
- Which calendar/session source determined that endpoint?
- Which candle was selected for the origin and endpoint?
- Was the evidence exact or selected under an explicit approved session rule?
- Which methodology version produced the observation?
- Are two observations methodologically comparable?
- Can observations be filtered by status, action, symbol, window, and methodology?

Sprint 15 should not yet answer:

- Was a recommendation successful?
- What is its hit rate?
- What confidence should future recommendations receive?
- Did the recommendation cause the market move?
- What realized portfolio return did the user earn?

---

# 3. Architectural Baseline

Sprint 14 provides:

```text
HistoricalRecommendationState
        +
HistoricalObservationWindow
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
Outcome CLI
```

Sprint 15 should extend this through explicit methodology:

```text
HistoricalRecommendationState
        +
Observation Methodology
        ├─ window policy
        ├─ session/calendar policy
        └─ evidence-selection policy
        ↓
Resolved observation endpoint
        ↓
Selected price evidence + provenance
        ↓
Outcome observation
        ↓
Methodology-aware query/aggregation
```

---

# 4. Core Design Rules

1. No hidden trading calendar.
2. No hidden nearest-date lookup.
3. Every session-derived endpoint must identify the session policy/source.
4. Every selected price point must identify the evidence-selection rule.
5. Methodology identity must be explicit in output.
6. Existing `ELAPSED_DAYS + exact` behavior must remain supported and unchanged.
7. Trading-session semantics must be deterministic.
8. Pure models/calculators must not access network data.
9. Session/calendar lookup must be behind a typed boundary.
10. No persistence migration until a separate requirement justifies it.
11. No effectiveness/confidence scoring in Sprint 15.
12. No automatic reinterpretation of raw price movement as total return or performance.
13. Missing session/evidence data must remain visible.
14. CLI may compose policies but may not own methodology logic.
15. E2E tests must include weekends or non-session gaps.

---

# 5. Explicit Non-Goals

Sprint 15 will not implement:

- recommendation success/failure labels;
- hit rate;
- recommendation effectiveness score;
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

# 6. Proposed Canonical Terminology

## Observation Methodology

A versioned contract describing how an outcome observation is constructed.

It should identify at least:

```text
methodology_id
methodology_version
window policy
endpoint policy
price evidence-selection policy
```

## Trading Session

One explicitly identified market session eligible for counting in a session-based observation window.

A session model must not be inferred from “weekday” alone.

## Session Calendar / Provider

A typed boundary that resolves valid sessions for an instrument/exchange context.

## Endpoint Resolution

The deterministic process that maps:

```text
origin
+ observation window
→ intended endpoint
```

## Evidence Selection

The deterministic process that maps an intended endpoint to an acceptable persisted price point.

Selection must never be an unbounded “closest date”.

---

# 7. Proposed Task Sequence

## Task 1 — Methodology Identity Models

### Goal

Define immutable methodology contracts before adding session logic.

### Proposed models

```text
HistoricalOutcomeMethodology
HistoricalEvidenceSelectionPolicy
HistoricalEndpointPolicy
```

### Requirements

- stable methodology ID;
- explicit version;
- immutable;
- JSON-ready;
- no repository access;
- no calculation.

### Initial methodology

Preserve Sprint 14 behavior as an explicit methodology, for example:

```text
ELAPSED_DAYS_EXACT_CLOSE
version 1
```

---

## Task 2 — Market Session Models

### Goal

Define canonical session vocabulary.

### Proposed models

```text
HistoricalMarketSession
HistoricalSessionCalendarIdentity
```

### Required concepts

- session date/key;
- open/close timestamp where available;
- timezone;
- exchange/calendar identity;
- provenance/source;
- deterministic ordering.

Do not yet add remote calendar fetching.

---

## Task 3 — Local Session Calendar Boundary

### Goal

Provide a typed read-only boundary for session resolution.

Before implementation, audit existing candle/exchange metadata.

Preferred first implementation should be local and deterministic.

The boundary must not assume that every weekday is a trading session unless that rule is explicitly represented as a methodology and documented as synthetic.

---

## Task 4 — Trading-Session Observation Window

### Goal

Add the first session-aware window kind.

Candidate:

```text
TRADING_SESSIONS
```

Example:

```text
5 trading sessions after origin
```

### Requirements

- uses session provider explicitly;
- no weekend arithmetic shortcut;
- explicit origin inclusion/exclusion rule;
- explicit endpoint session;
- explicit not-mature semantics;
- timezone-aware.

---

## Task 5 — Evidence Selection Policy

### Goal

Separate endpoint resolution from price evidence selection.

Initial supported policies should remain narrow.

Candidates:

```text
EXACT_TIMESTAMP
SESSION_CLOSE_EXACT
```

Do not add generic `NEAREST`.

If a bounded fallback is ever added, its direction and bound must be explicit.

---

## Task 6 — Methodology-Aware Price Evidence

### Goal

Extend price-evidence output so selected evidence explains:

- intended endpoint;
- selected evidence timestamp;
- selection policy;
- session identity where relevant;
- source/currency/resolution.

Existing exact evidence behavior must remain backward-compatible.

---

## Task 7 — Methodology-Aware Observation Service

### Goal

Refactor outcome orchestration to accept an explicit methodology rather than implicit policy wiring.

Conceptually:

```text
recommendation state
+ methodology
+ as_of
→ observation
```

### Requirements

- preserve Sprint 14 statuses;
- retain raw calculator;
- no persistence;
- no network access;
- deterministic output.

---

## Task 8 — Methodology Compatibility Model

### Goal

Define whether two outcome observations are methodologically comparable.

Potential statuses:

```text
COMPATIBLE
PARTIALLY_COMPATIBLE
INCOMPATIBLE
```

The exact model must be justified by real comparison needs.

No statistical inference yet.

---

## Task 9 — Outcome Query Filters

### Goal

Add read-only filtering over produced observations.

Candidate filters:

- recommendation key;
- symbol;
- action;
- observation status;
- window kind/value;
- methodology ID/version;
- origin time range.

Do not add persistence merely to support filtering; in-memory composition is acceptable at current scale.

---

## Task 10 — Aggregation by Explicit Methodology

### Goal

Prevent aggregation from silently mixing incompatible methodologies.

Requirements:

- methodology identity visible;
- reject or separate incompatible groups;
- preserve sample counts;
- no success/effectiveness metric.

---

## Task 11 — Methodology-Aware CLI

### Goal

Expose explicit methodology selection and output.

CLI should show:

- methodology ID/version;
- window semantics;
- session/calendar identity where used;
- evidence-selection policy;
- status/sample coverage;
- raw descriptive movement only.

---

## Task 12 — Realistic Session-Aware E2E Fixture

### Required scenario

Use deterministic local evidence crossing at least one non-session gap.

Example flow:

```text
recommendation on Friday
→ 1 trading session window
→ weekend skipped by explicit calendar
→ Monday session endpoint
→ exact session-close evidence
→ COMPLETE observation
```

Also include:

- not-mature case;
- missing session evidence;
- methodology identity in CLI JSON;
- aggregation separation/compatibility behavior;
- no outcome persistence.

---

## Task 13 — Documentation and Sprint 15 Review

Update canonical docs after implementation.

Create:

```text
docs/SPRINT_15_REVIEW.md
```

Reconcile:

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/SPRINT_15_PLAN.md
```

---

# 8. Architecture Guardrails

Allowed:

```text
Outcome Observation Service
→ explicit methodology
→ session/calendar boundary
→ price-evidence boundary
→ pure calculator
```

Forbidden:

```text
Outcome model → network
CLI → session arithmetic
CLI → nearest-date selection
Calculator → calendar lookup
Aggregator → mixed methodologies without explicit grouping/compatibility
Outcome service → current quote fallback
History archive → mutation
```

---

# 9. Data / Persistence Strategy

Default Sprint 15 decision:

```text
History schema target = 2
Outcome observations = on demand
Methodology definitions = code/value contracts initially
```

Do not introduce schema v3 unless a concrete Sprint 15 task proves persistence is required.

If a calendar needs persisted local data, determine ownership separately:

```text
market evidence storage
≠
History outcome persistence
```

Do not place market-calendar data into History merely because outcome analysis consumes it.

---

# 10. Backward Compatibility

Sprint 14 behavior must remain valid.

Existing methodology:

```text
ELAPSED_DAYS
+
exact timestamp
+
local candle close
```

must still produce the same endpoint/evidence/result semantics.

Session-aware methodology is an addition, not a silent behavior change.

---

# 11. Testing Strategy

Required categories:

- methodology model validation;
- methodology version identity;
- session model validation;
- deterministic session ordering;
- weekend/non-session gap behavior;
- timezone/DST behavior;
- origin session inclusion/exclusion;
- not-mature session window;
- missing calendar data;
- missing exact session evidence;
- evidence-selection provenance;
- Sprint 14 backward compatibility;
- methodology compatibility;
- aggregation separation;
- CLI JSON;
- realistic session-aware E2E;
- full regression suite.

Commands:

```powershell
python -m pytest tests\<focused-test>.py -q
python -m pytest -q
```

---

# 12. Definition of Done

Sprint 15 is complete only when:

- methodology identity/version is canonical;
- Sprint 14 exact methodology is explicitly represented;
- market-session vocabulary is canonical;
- one deterministic session/calendar boundary exists;
- `TRADING_SESSIONS` semantics are explicit;
- endpoint and evidence-selection policies are separate;
- session-aware outcome observation works without hidden fallback;
- methodology identity is preserved through observation and CLI;
- incompatible methodologies are not silently aggregated;
- Sprint 14 behavior remains regression-safe;
- realistic weekend/non-session E2E tests pass;
- full regression suite passes;
- documentation is aligned;
- Sprint 15 review exists;
- working tree is clean;
- all changes are committed and pushed.

---

# 13. Recommended First Implementation Package

After this planning package, start with:

```text
Task 1 — Methodology Identity Models
```

Before writing code, audit only:

- `historical_outcome_models.py`;
- `historical_observation_window.py`;
- `historical_outcome_price_evidence.py`;
- `historical_outcome_observation_service.py`;
- `historical_outcome_aggregation.py`;
- candle/exchange metadata conventions.

The first code package should introduce methodology vocabulary without changing endpoint behavior.

---

# 14. Sprint Statement

> Sprint 14 taught Investment Terminal to observe what happened afterward. Sprint 15 will make the meaning of “afterward” explicit enough for real market sessions, without sacrificing provenance or inventing confidence.
