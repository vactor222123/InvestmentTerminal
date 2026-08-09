# Sprint 15 Review — Historical Outcome Methodology Hardening

**Sprint:** 15  
**Status:** Implementation Complete — Final Repository Verification Pending  
**Theme:** Historical Outcome Methodology Hardening  
**Baseline before Sprint 15 implementation:** `907fe27`  
**Implementation baseline before final documentation:** `0c766ee`

---

# 1. Executive Summary

Sprint 15 achieved its primary goal.

Historical recommendation outcomes are no longer limited to an implicit:

```text
elapsed days
+
exact timestamp
```

interpretation.

The system now has explicit, versioned methodology contracts and a deterministic trading-session-aware path:

```text
HistoricalRecommendationState
        +
HistoricalOutcomeMethodology
        +
explicit local market-session calendar
        ↓
session-aware endpoint resolution
        ↓
exact-only evidence selection
        ↓
methodology-aware historical observation
        ↓
methodology-aware query / aggregation / CLI
```

The sprint hardened methodology without introducing success labels, predictive confidence, causality, or portfolio-performance claims.

---

# 2. What Sprint 15 Delivered

## 2.1 Methodology Identity

Canonical immutable models now identify:

```text
HistoricalOutcomeMethodology
HistoricalEndpointPolicy
HistoricalEvidenceSelectionPolicy
```

The Sprint 14 methodology is explicitly named:

```text
ELAPSED_DAYS_EXACT_CLOSE@1
```

This makes backward-compatible behavior identifiable instead of implicit.

## 2.2 Market-Session Vocabulary

Canonical session contracts:

```text
HistoricalMarketSession
HistoricalSessionCalendarIdentity
```

A session carries:

- stable session key;
- session date;
- explicit open timestamp;
- explicit close timestamp;
- calendar identity/version;
- timezone;
- provenance/source.

No session is inferred from a weekday.

## 2.3 Deterministic Local Calendar Boundary

`HistoricalLocalSessionCalendar` provides read-only deterministic access to explicitly supplied sessions.

It does not:

- fetch the network;
- infer holidays;
- infer sessions from candles;
- mutate History;
- own persistence.

## 2.4 Trading-Session Window

Sprint 15 added:

```text
TRADING_SESSIONS
```

Canonical v1 endpoint semantics:

```text
origin_at
→ sessions with opens_at > origin_at
→ count N sessions
→ Nth session is endpoint session
→ endpoint_at = endpoint session closes_at
```

Maturity:

```text
as_of >= endpoint_at
```

Insufficient calendar coverage is an explicit error.

## 2.5 Exact Evidence Selection

Supported policies:

```text
EXACT_TIMESTAMP_CLOSE@1
SESSION_CLOSE_EXACT@1
```

No:

```text
NEAREST
PREVIOUS_CLOSE fallback
NEXT_CLOSE fallback
current-price fallback
```

A missing exact session-close candle remains missing evidence.

## 2.6 Methodology-Aware Provenance

Price evidence can now explain:

- methodology identity;
- intended endpoint;
- selected evidence timestamp;
- evidence-selection policy;
- raw price point;
- session identity;
- calendar provenance.

This preserves the distinction between endpoint resolution and evidence selection.

## 2.7 Methodology-Aware Observation

`HistoricalMethodologyAwareObservationService` accepts:

```text
recommendation state
+ observation window
+ methodology
+ as_of
+ resolution
```

Origin evidence remains exact at the archived recommendation timestamp.

Endpoint evidence follows the explicit methodology.

Existing observation statuses remain:

```text
COMPLETE
PARTIAL
UNAVAILABLE
NOT_MATURE
```

## 2.8 Methodology Compatibility

Structural compatibility is explicit:

```text
COMPATIBLE
PARTIALLY_COMPATIBLE
INCOMPATIBLE
```

This model deliberately does not imply statistical comparability.

## 2.9 Query / Filtering

Methodology-aware observations can be filtered in memory by:

- recommendation key;
- symbol;
- action;
- status;
- window kind/value;
- methodology ID/version;
- origin time range.

No outcome persistence was introduced to support querying.

## 2.10 Methodology-Safe Aggregation

Aggregation no longer has to silently mix methodologies.

```text
summarize_one
→ one exact methodology identity only

summarize_grouped
→ one summary per exact methodology identity
```

Different methodology versions are separated.

Mean and median remain raw descriptive price movement over `COMPLETE` observations only.

## 2.11 Methodology-Aware CLI

A separate CLI was added rather than changing the Sprint 14 CLI.

It exposes:

- methodology ID/version;
- window semantics;
- endpoint policy;
- evidence-selection policy;
- calendar identity/source for session methodology;
- observation status/coverage;
- raw descriptive movement.

Session methodology requires an explicit local JSON calendar.

## 2.12 Realistic Session-Aware E2E

A deterministic fixture covers:

```text
Friday recommendation
→ weekend
→ Monday explicit session
→ Monday session close
→ exact close evidence
→ COMPLETE
```

It also verifies:

- `NOT_MATURE` before Monday close;
- missing exact Monday close → `PARTIAL`;
- no nearest fallback around the endpoint;
- methodology identity;
- session/calendar provenance;
- methodology-aware aggregation;
- JSON-ready output;
- no outcome table persistence.

---

# 3. Architectural Review

## 3.1 Source-of-Truth Hierarchy Remains Clean

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Local candle database
    historical market-data evidence

Explicit local session calendar
    methodology input / session evidence

Outcome observation
    rebuildable derived result

Outcome aggregation
    rebuildable descriptive result
```

No derived outcome became canonical historical fact.

## 3.2 Endpoint Resolution and Evidence Selection Are Separate

This is one of the most important Sprint 15 outcomes.

```text
window + calendar
→ intended endpoint

intended endpoint + evidence-selection policy
→ acceptable persisted price evidence
```

This prevents missing market evidence from silently changing the historical question being asked.

## 3.3 CLI Remains a Composition Boundary

The CLI selects and wires explicit policies.

It does not own:

- trading-session arithmetic;
- evidence fallback;
- outcome calculation;
- methodology compatibility;
- aggregate math.

## 3.4 Persistence Boundary Was Preserved

Sprint 15 added no History schema migration.

Final decision:

```text
History schema target = 2
outcomes = derived/on demand
aggregates = derived/on demand
session calendars = explicit local input
```

This remains appropriate because no current requirement needs persisted outcome materialization.

---

# 4. Guardrail Review

## Preserved

- no hindsight leakage;
- no current-price fallback;
- no hidden nearest-date selection;
- no implicit trading calendar;
- no network access inside pure calculations;
- no outcome persistence;
- no History archive mutation;
- no effectiveness score;
- no predictive confidence;
- no causal inference;
- no raw-price-to-portfolio-performance reinterpretation.

## Explicitly Deferred

- generic bounded fallback policy;
- remote exchange calendar provider;
- total-return/dividend-adjusted outcome;
- FX normalization;
- portfolio attribution;
- success labels;
- hit rate;
- confidence calibration;
- factor-effectiveness research;
- Knowledge Domain.

---

# 5. Backward Compatibility Review

Sprint 14 exact behavior remains available as:

```text
ELAPSED_DAYS_EXACT_CLOSE@1
```

The original Sprint 14 CLI remains unchanged.

The session-aware path is additive:

```text
TRADING_SESSIONS_EXACT_CLOSE@1
```

This was the correct compatibility strategy because it avoids silently changing historical meaning for existing callers.

---

# 6. Testing Review

Sprint 15 added focused coverage for:

- methodology model validation;
- version identity;
- session model validation;
- deterministic session ordering;
- explicit missing-session behavior;
- Friday/weekend/Monday session resolution;
- origin inclusion/exclusion semantics;
- session-close maturity;
- exact-only evidence selection;
- no nearest fallback;
- methodology-aware provenance;
- Sprint 14 methodology compatibility;
- structural methodology compatibility;
- outcome filtering;
- methodology-safe aggregation;
- methodology-aware CLI argument/calendar behavior;
- realistic session-aware E2E.

Final closure still requires running the full suite after this documentation package is applied.

---

# 7. Deviations / Clarifications From the Original Plan

## 7.1 Existing Sprint 14 CLI Was Not Refactored

Instead of modifying it, Sprint 15 added a separate methodology-aware CLI.

Reason:

- preserve Sprint 14 regression safety;
- keep old `--window-days` semantics stable;
- avoid silently changing established behavior.

This is a positive architectural deviation.

## 7.2 Origin Evidence Uses Exact Timestamp Policy

For session-aware outcomes, the endpoint uses:

```text
SESSION_CLOSE_EXACT@1
```

but origin evidence remains:

```text
EXACT_TIMESTAMP_CLOSE@1
```

at `state.generated_at`.

This is necessary because a recommendation origin timestamp is not necessarily a market-session close.

## 7.3 Session Calendar Is Explicit Local Input

Sprint 15 did not add a remote exchange-calendar service.

This was intentional.

The sprint goal was to establish deterministic methodology semantics first, not external calendar acquisition.

---

# 8. Remaining Risks

## 8.1 Calendar Completeness

A local explicit calendar can be incomplete.

Current behavior is correct: insufficient sessions produce an explicit resolution error.

Future work may add a verified calendar source, but should preserve provenance.

## 8.2 Session Identity vs Instrument Venue

The current methodology can consume an explicit calendar, but broader production use will eventually need a canonical mapping between instrument/venue and appropriate session calendar.

That mapping must not be guessed.

## 8.3 Raw Close Price Is Not Total Return

Current outcomes do not include:

- distributions;
- dividend reinvestment;
- corporate-action normalization beyond what the stored series provides;
- FX conversion.

The product must continue to label this as raw price movement.

## 8.4 Small Sample Risk

Methodology correctness does not make a historical sample statistically meaningful.

Any next-step effectiveness analysis must enforce sample-size and uncertainty rules.

---

# 9. Sprint 15 Acceptance Checklist

Implementation:

```text
[x] methodology identity/version is canonical
[x] Sprint 14 exact methodology is explicitly represented
[x] market-session vocabulary is canonical
[x] deterministic local session/calendar boundary exists
[x] TRADING_SESSIONS semantics are explicit
[x] endpoint and evidence-selection policies are separate
[x] session-aware observation has no hidden fallback
[x] methodology identity is preserved through observation
[x] methodology identity is exposed by CLI
[x] incompatible identities are not silently aggregated
[x] Sprint 14 exact behavior remains supported
[x] realistic weekend/session-gap E2E exists
[x] no outcome persistence was introduced
[x] History schema remains version 2
[x] Sprint 15 review exists
```

Final repository closure:

```text
[ ] documentation diff passes git diff --check
[ ] full regression suite passes after documentation update
[ ] Task 13 docs committed
[ ] Task 13 pushed to origin/develop
[ ] working tree clean
```

---

# 10. Recommendation for the Next Sprint

The next sprint should be a **research-protocol sprint**, not a confidence-model sprint.

Proposed theme:

```text
Statistically Honest Outcome Research Foundation
```

It should define before scoring anything:

1. eligible observation population;
2. minimum sample size;
3. exact methodology grouping;
4. treatment of missing/not-mature evidence;
5. observation-window grouping;
6. action/symbol/cohort grouping;
7. survivorship and selection-bias safeguards;
8. uncertainty/interval reporting;
9. multiple-comparison discipline where applicable;
10. explicit non-causal wording.

Only after those rules are implemented and validated should the system consider:

```text
recommendation effectiveness
hit rate
confidence calibration
factor-effectiveness analysis
```

---

# 11. Final Assessment

Sprint 15 materially improves historical-outcome correctness.

The key product improvement is not simply “trading days support.”

It is this separation:

```text
What endpoint does the methodology ask for?
        ≠
What market evidence is available?
```

Combined with explicit methodology identity, this makes future historical research more reproducible and much harder to contaminate with hidden fallback behavior.

Sprint 15 should be considered complete once the final documentation package is applied, the full regression suite passes, and the resulting documentation commit is pushed with a clean working tree.
