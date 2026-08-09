# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 18 — Explicit Historical Archive Continuity
implementation complete; final repository verification pending
```

## Completed historical-intelligence foundation

### Sprint 12

Immutable historical Review Package archive, integrity, History SQLite projection, typed imports, and timeline foundation.

### Sprint 13

Historical navigation, compatibility, comparison, replay, read-only History CLIs, migration/import-state foundation, and realistic History E2E.

### Sprint 14

Canonical outcome observations, exact local candle evidence, raw close-price movement, explicit observation states, descriptive aggregation, CLI, and outcome E2E.

### Sprint 15

Explicit methodology identity, deterministic market-session semantics, exact-only evidence selection, methodology-aware observations, filtering, methodology-safe aggregation, CLI, and session-aware E2E.

### Sprint 16

Versioned descriptive research protocol, explicit eligibility/coverage, exact cohorts, sample sufficiency, descriptive statistics, standard error, claim boundaries, population warnings, read-only research CLI, and multi-observation E2E.

### Sprint 17

Research population frame, selection accounting, temporal boundary completeness, source import quality, canonical provenance summary, compatibility migration, and provenance E2E.

### Sprint 18

Delivered:

```text
HistoricalArchiveCadencePolicy
HistoricalArchiveExpectedTimestampService
HistoricalArchiveGapAssessment
HistoricalArchiveGapAssessmentService
HistoricalArchiveRepositoryGapService
explicit archive-continuity integration into population completeness
research-service continuity wiring
CLI cadence opt-in
repository-backed continuity E2E
canonical optional ARCHIVE_GAP_ASSESSMENT provenance extension
CLI continuity/provenance compatibility contracts
```

## Canonical Archive Continuity

Archive continuity is assessed only from an explicit cadence contract.

Canonical cadence identity:

```text
FIXED_INTERVAL_ARCHIVE_CADENCE@1
```

Version 1 uses:

```text
timestamp basis = GENERATED_AT
anchor_at = explicit timezone-aware timestamp
interval_seconds = explicit positive interval
```

It deliberately does not infer:

```text
business days
exchange sessions
holidays
retry schedules
operational downtime
```

Expected timestamps are generated from the explicit cadence and compared exactly with repository snapshot `generated_at` values.

Canonical gap statuses:

```text
COMPLETE
GAPS
NO_EXPECTATION
```

`COMPLETE` means every expected timestamp in the assessed interval is present.

`GAPS` means at least one expected timestamp is missing.

`NO_EXPECTATION` means the assessed cadence/interval produced no expected timestamps; it is not treated as proof of continuity.

Unexpected off-grid observed snapshots remain visible diagnostics and do not silently alter the expected cadence.

## Temporal Population Completeness

Boundary coverage and internal archive continuity remain independent dimensions.

Boundary statuses:

```text
COVERED
PARTIAL
UNKNOWN
```

Internal continuity statuses:

```text
NOT_ASSESSED
COMPLETE
GAPS
```

Examples:

```text
boundary=COVERED / internal=GAPS
boundary=PARTIAL / internal=COMPLETE
```

are valid because spanning the requested source interval and satisfying the expected archive cadence are different questions.

Without an explicit archive gap assessment, internal continuity remains:

```text
NOT_ASSESSED
```

No cadence is inferred from observed snapshots.

## Canonical Research Provenance

The four core provenance components remain:

```text
HistoricalOutcomeResearchProvenanceSummary
├── SOURCE_IMPORT_QUALITY
├── POPULATION_COMPLETENESS
├── POPULATION_FRAME
└── SELECTION_ACCOUNTING
```

Sprint 18 adds:

```text
optional provenance extensions
└── ARCHIVE_GAP_ASSESSMENT
```

The optional archive-gap component contains detailed expected/missing/unexpected timestamp diagnostics.

It does not change the legacy/core provenance completeness denominator:

```text
4/4 components
```

Therefore absence of explicit cadence does not make an otherwise complete Sprint 17 provenance envelope incomplete.

When an archive gap assessment is present, provenance validates consistency between:

```text
archive gap COMPLETE     ↔ internal continuity COMPLETE
archive gap GAPS         ↔ internal continuity GAPS
archive gap NO_EXPECTATION ↔ internal continuity NOT_ASSESSED
```

## Research and CLI Boundaries

`HistoricalOutcomeResearchService` remains persistence-agnostic.

It receives immutable `HistoricalArchiveGapAssessment` data and does not open History SQLite or infer cadence.

Repository-backed composition remains at the application/CLI boundary:

```text
explicit cadence
→ expected GENERATED_AT timestamps
→ HistoricalSnapshotRepository
→ repository gap assessment
→ research service
→ population completeness
→ research provenance
```

CLI cadence assessment is opt-in through:

```text
--archive-cadence-anchor
--archive-cadence-interval-seconds
```

Both options must be supplied together.

Cadence assessment also requires explicit:

```text
--origin-from
--origin-to
```

Without cadence options, CLI behavior remains backward-compatible and internal continuity remains `NOT_ASSESSED`.

## CLI Output Contract

Human output preserves the core provenance denominator:

```text
Provenance   : 4/4 components; complete=True
```

When cadence is supplied, continuity diagnostics may additionally show:

```text
Completeness : COVERED / internal=GAPS
Archive gaps : GAPS / missing=1 / unexpected=0
```

JSON output exposes cadence and gap diagnostics while canonical cohort provenance carries the optional `archive_gap_assessment` extension.

## Stable Research Guardrails

Sprint 18 preserves all prior research claim boundaries:

- no hindsight leakage;
- no current-price fallback;
- no hidden nearest-date substitution;
- no implicit exchange calendar;
- no implicit archive cadence;
- no network call inside pure research calculation;
- no outcome/research persistence;
- no success/failure scoring;
- no hit rate or win rate;
- no recommendation-effectiveness scoring;
- no predictive confidence;
- no causal inference;
- no representativeness claim from boundary coverage or archive continuity;
- no portfolio-performance wording for raw price movement;
- explicit population-selection warnings;
- explicit sample-size boundary;
- CLI remains composition/rendering only.

Archive continuity proves only agreement with the supplied expected-cadence contract for the assessed interval.

It does not prove that the cadence itself is operationally correct, that the population is unbiased, or that research conclusions are inferentially valid.

## Persistence Status

Sprint 18 introduces no new persistence.

```text
History schema target = 2
archive cadence policy = runtime/versioned contract
archive gap assessment = derived/on demand
outcome observations = derived/on demand
research provenance = derived/on demand
research results = derived/on demand
```

No History schema v3 was introduced.

## E2E Coverage

Sprint 18 covers:

```text
cadence validation
expected timestamp generation
exact gap assessment
repository-backed gap composition
population-completeness integration
research continuity wiring
real History SQLite COMPLETE/GAPS paths
JSON and human CLI continuity rendering
optional provenance extension compatibility
legacy 4/4 provenance denominator
```

## Testing Status

Focused Sprint 18 tests are implemented.

Final repository closure requires:

```text
python -m pytest -q
```

to pass after applying this documentation package.

## Deferred Capabilities

Still not implemented:

- business-day archive cadence;
- exchange-session archive cadence;
- holiday-aware archive cadence;
- operational retry/downtime cadence semantics;
- automatic cadence discovery;
- population-universe representativeness model;
- recommendation success/failure labels;
- hit rate / win rate;
- recommendation-effectiveness scoring;
- predictive confidence calibration;
- inferential confidence intervals;
- hypothesis tests;
- multiple-comparison inference;
- factor-effectiveness inference;
- causal inference;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- portfolio attribution;
- outcome/research persistence;
- autonomous trading;
- broker execution;
- Knowledge Domain.

## Next Decision

Sprint 18 closes the explicit archive-continuity hardening path selected after Sprint 17.

The next milestone should not add inferential or effectiveness claims merely because archive continuity is now measurable.

A future milestone can either define richer source/population contracts or move to the deferred Knowledge Domain, but any new semantics must remain explicit, versioned, deterministic, and evidence-grounded.
