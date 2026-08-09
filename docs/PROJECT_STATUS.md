# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 17 — Research Provenance and Population Quality Hardening
implementation complete; final documentation/repository verification
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

Delivered:

```text
HistoricalOutcomeResearchPopulationFrame
HistoricalOutcomeResearchPopulationFrameService
HistoricalOutcomeSelectionReasonCount
HistoricalOutcomeSelectionAccounting
HistoricalOutcomeSelectionAccountingService
HistoricalOutcomePopulationCompletenessAssessment
HistoricalOutcomePopulationCompletenessService
HistoricalOutcomeSourceImportQualityAssessment
HistoricalOutcomeSourceImportQualityService
HistoricalOutcomeResearchProvenanceSummary
HistoricalOutcomeResearchProvenanceSummaryService
research-service provenance integration
research CLI provenance rendering
provenance compatibility layer
production-style provenance E2E
```

## Canonical Research Provenance

Canonical research provenance now uses one envelope:

```text
HistoricalOutcomeResearchProvenanceSummary
├── SOURCE_IMPORT_QUALITY
├── POPULATION_COMPLETENESS
├── POPULATION_FRAME
└── SELECTION_ACCOUNTING
```

The envelope is diagnostic and compositional.

It deliberately does not define a single quality score, pass/fail verdict, representativeness score, or inference-readiness score.

## Source Import Quality

Import quality is assessed over unique `origin_snapshot_id` values rather than raw observation count.

Canonical statuses:

```text
COMPLETE
PARTIAL
UNKNOWN
```

`COMPLETE` means all unique source snapshots have canonical `IMPORTED` lifecycle state.

`PARTIAL` means at least one source snapshot is non-IMPORTED or has no canonical import state.

This is import-lifecycle provenance only.

It does not establish that the source population is representative or complete in time.

## Temporal Population Completeness

Canonical temporal completeness statuses:

```text
COVERED
PARTIAL
UNKNOWN
```

The assessment compares observed source origin timestamps against an explicitly requested origin interval.

`COVERED` means the observed source frame spans the requested temporal boundaries.

Internal archive continuity remains:

```text
NOT_ASSESSED
```

because no canonical expected snapshot cadence currently exists.

Therefore temporal boundary coverage is not equivalent to “no missing snapshots”.

## Population Frame

The population frame makes the pre-selection denominator explicit:

```text
source_observation_count
selected_candidate_count
excluded_by_selection_count
selection_fraction
selection_applied
```

This distinguishes source population size from query-selected candidate size.

## Selection Accounting

Selection accounting explains why source observations were excluded by the research query.

Canonical reasons include:

```text
RECOMMENDATION_KEY
SYMBOL
ACTION
STATUS
WINDOW_KIND
WINDOW_VALUE
METHODOLOGY_ID
METHODOLOGY_VERSION
ORIGIN_FROM
ORIGIN_TO
```

Reasons are not exclusive.

One observation can fail multiple predicates, so:

```text
total_reason_failures
```

is diagnostic and is not required to equal:

```text
excluded_observation_count
```

## Research Result Boundary

`HistoricalOutcomeResearchCohortResult` now owns canonical:

```text
provenance
```

instead of treating import quality, temporal completeness, population frame, and selection accounting as unrelated result concepts.

For compatibility with pre-provenance callers, read-only Python properties and transitional top-level serialization aliases remain available.

Canonical new consumers should use:

```text
result.provenance
payload["provenance"]
```

## Canonical Research Semantics

Sprint 16 research semantics remain unchanged:

```text
DESCRIPTIVE_OUTCOME_RESEARCH@1
eligible statuses: COMPLETE
uncertainty: SAMPLE_STANDARD_ERROR
claims: DESCRIPTIVE_ONLY
```

Sprint 17 did not introduce:

```text
hit rate
win rate
success probability
effectiveness
predictive confidence
causal inference
hypothesis tests
confidence intervals
```

## Persistence Status

Sprint 17 introduced no outcome, provenance, or research persistence.

```text
History schema target = 2
outcome observations = derived/on demand
research provenance = derived/on demand
research results = derived/on demand
```

No History schema v3 was introduced.

## Architecture Boundaries

The research service remains persistence-agnostic.

`HistoricalImportStateRepository` is used at the application/CLI boundary to build immutable import-quality assessment data.

Research orchestration receives the assessment rather than opening History SQLite itself.

The CLI remains composition/rendering only and owns no provenance or research mathematics.

## E2E Coverage

Sprint 17 adds a production-style provenance E2E using:

```text
History SQLite
local market SQLite
historical import lifecycle
methodology-aware observations
research query
research provenance
research result
```

The fixture verifies a mixed import lifecycle:

```text
2 IMPORTED
1 METADATA_ONLY
```

and confirms:

```text
source observations = 3
selected candidates = 1
source import quality = PARTIAL
temporal completeness = COVERED
selection reasons = ORIGIN_FROM + ORIGIN_TO
eligible research sample = 1
```

It also verifies the canonical provenance envelope and transitional serialization aliases.

## Stable Guardrails

- no hindsight leakage;
- no current-price fallback;
- no hidden nearest-date substitution;
- no implicit exchange calendar;
- no network call inside pure research calculation;
- no outcome/research persistence;
- no success/failure scoring;
- no hit rate;
- no effectiveness scoring;
- no predictive confidence;
- no causal inference;
- no archive-continuity claim without expected cadence;
- no representativeness claim from provenance completeness;
- no portfolio-performance wording for raw price movement;
- explicit population-selection warnings;
- explicit sample-size boundary;
- CLI remains composition/rendering only.

## Testing Status

Sprint 17 includes focused tests for:

```text
population frame
selection provenance
CLI population-frame rendering
selection-reason accounting
selection-accounting integration
temporal completeness
completeness integration
source import quality
import-quality integration
provenance summary
provenance integration
compatibility migration
provenance E2E
```

The full regression suite was green immediately before the Sprint 17 documentation package.

Final repository closure requires rerunning the full suite after applying these docs.

## Deferred Capabilities

Not implemented:

- success/failure labels;
- hit rate / win rate;
- recommendation-effectiveness scoring;
- predictive confidence calibration;
- inferential confidence intervals;
- hypothesis tests;
- multiple-comparison inference;
- factor-effectiveness inference;
- causal inference;
- expected archive cadence;
- archive-gap inference;
- population-universe representativeness model;
- dividend-adjusted total return;
- FX-adjusted outcomes;
- portfolio attribution;
- outcome/research persistence;
- autonomous trading;
- broker execution;
- Knowledge Domain.

## Next Decision

Do not infer that provenance completeness proves recommendation effectiveness or inferential validity.

A future inferential/comparative milestone still requires explicit versioned contracts for estimand, source/target population assumptions, comparison semantics, interval/test methodology, multiple-comparison rules, selection/survivorship treatment, and claim vocabulary.
