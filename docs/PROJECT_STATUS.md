# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 15 — Historical Outcome Methodology Hardening
implementation complete; final documentation/repository verification
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

### Sprint 15

- `HistoricalOutcomeMethodology`;
- `HistoricalEndpointPolicy`;
- `HistoricalEvidenceSelectionPolicy`;
- `HistoricalMarketSession`;
- `HistoricalSessionCalendarIdentity`;
- deterministic `HistoricalLocalSessionCalendar`;
- `HistoricalTradingSessionWindowPolicy`;
- `TRADING_SESSIONS` window semantics;
- `HistoricalSelectedPriceEvidence`;
- exact-only evidence-selection service;
- `HistoricalMethodologyAwarePriceEvidence`;
- methodology-aware price-evidence service;
- methodology-aware observation service/result;
- structural methodology compatibility model/service;
- in-memory outcome query/filter service;
- methodology-aware aggregation grouped by exact identity;
- methodology-aware outcome CLI;
- realistic session-aware Friday/weekend/Monday E2E fixture;
- explicit no-fallback behavior around missing session-close evidence.

## Canonical Sprint 15 methodologies

### Sprint 14-compatible methodology

```text
ELAPSED_DAYS_EXACT_CLOSE@1
window: ELAPSED_DAYS
endpoint policy: ELAPSED_DURATION_UTC@1
endpoint evidence: EXACT_TIMESTAMP_CLOSE@1
price field: CLOSE
```

### Session-aware methodology

```text
TRADING_SESSIONS_EXACT_CLOSE@1
window: TRADING_SESSIONS
endpoint policy: TRADING_SESSION_CLOSE@1
endpoint evidence: SESSION_CLOSE_EXACT@1
price field: CLOSE
calendar: explicit local HistoricalSessionCalendarIdentity
```

Origin recommendation evidence remains exact at the archived recommendation timestamp through `EXACT_TIMESTAMP_CLOSE@1`.

## Canonical trading-session semantics

For Sprint 15 v1:

```text
origin_at
→ select explicit sessions whose opens_at > origin_at
→ count N sessions
→ endpoint session = Nth selected session
→ endpoint_at = endpoint session closes_at
→ mature when as_of >= endpoint_at
```

No weekday arithmetic is used.

No implicit holiday model is used.

If the supplied local calendar does not contain enough sessions, endpoint resolution fails explicitly.

## Canonical evidence-selection semantics

Supported:

```text
EXACT_TIMESTAMP_CLOSE@1
SESSION_CLOSE_EXACT@1
```

Not supported:

```text
NEAREST
PREVIOUS_CLOSE fallback
NEXT_CLOSE fallback
current-price fallback
unbounded date substitution
```

Missing exact endpoint evidence remains visible as incomplete evidence rather than being substituted.

## Methodology compatibility semantics

Structural only:

```text
same methodology identity
→ COMPATIBLE

same window kind and price field,
but policy/version/identity differs
→ PARTIALLY_COMPATIBLE

different window kind or price field
→ INCOMPATIBLE
```

This does not establish statistical comparability.

## Aggregation rule

Methodology-aware aggregates must not silently mix methodology identities.

```text
summarize_one
→ exactly one methodology.identity_key

summarize_grouped
→ separate group per exact methodology.identity_key
```

Raw mean/median price movement remains descriptive only.

## Stable source-of-truth hierarchy

```text
Archived Review Package JSON
    canonical historical Review Package evidence

History SQLite
    rebuildable normalized historical projection

Local candle database
    persisted historical market-data evidence

Explicit local session calendar
    methodology input with source/provenance

Outcome observation
    rebuildable derived result

Methodology-aware aggregation
    rebuildable descriptive result
```

## Persistence status

Sprint 15 introduced no History persistence requirement.

```text
History schema target = 2
outcome observations = on demand
outcome aggregation = on demand
session calendar = explicit local methodology input
```

No History schema v3 was introduced.

## Stable guardrails

- no hindsight leakage;
- no silent present-day fallback;
- no unbounded nearest-date substitution;
- no implicit exchange calendar;
- no network call inside pure outcome calculation;
- no outcome persistence;
- no success/failure scoring;
- no confidence calibration;
- no causal claims;
- no portfolio-performance wording for raw price movement;
- CLI remains a composition/rendering boundary;
- Sprint 14 exact behavior remains supported.

## Deferred capabilities

Not implemented:

- recommendation success/failure labels;
- hit rate;
- recommendation-effectiveness scoring;
- predictive confidence calibration;
- factor-effectiveness inference;
- causal inference;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- portfolio performance attribution;
- tax-lot performance;
- outcome persistence/materialization;
- autonomous trading;
- broker execution;
- Knowledge Domain.

## Next decision

The next milestone should define a statistically honest effectiveness-research protocol before adding effectiveness or confidence metrics.

At minimum it should specify:

- eligible sample;
- minimum sample size;
- methodology grouping;
- missing-evidence handling;
- multiple-window handling;
- selection/survivorship safeguards;
- uncertainty reporting;
- descriptive vs inferential claims;
- non-causal interpretation.
