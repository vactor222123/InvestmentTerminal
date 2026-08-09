# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 16 — Statistically Honest Outcome Research Foundation
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

Delivered:

```text
HistoricalOutcomeResearchProtocol
HistoricalOutcomeEligibilityService
HistoricalOutcomeCohortService
HistoricalOutcomeResearchCoverageService
HistoricalOutcomeSampleSufficiencyService
HistoricalOutcomeDescriptiveSummaryService
HistoricalOutcomeUncertaintyService
HistoricalOutcomeResearchClaimBoundaryService
HistoricalOutcomeResearchService
HistoricalOutcomeResearchPopulationMetadataService
outcome_research CLI
multi-observation research E2E
```

Canonical protocol:

```text
DESCRIPTIVE_OUTCOME_RESEARCH@1
eligible statuses: COMPLETE
uncertainty: SAMPLE_STANDARD_ERROR
claims: DESCRIPTIVE_ONLY
minimum sample size: explicit per protocol instance
```

## Canonical Research Semantics

Research never silently pools incompatible methodology/window cohorts.

```text
METHODOLOGY_IDENTITY
WINDOW_KIND
WINDOW_VALUE
```

are canonical grouping dimensions for descriptive v1.

Coverage keeps incomplete evidence visible:

```text
COMPLETE
PARTIAL
UNAVAILABLE
NOT_MATURE
```

Only eligible observations enter descriptive statistics.

Sample sufficiency is explicit:

```text
SUFFICIENT
INSUFFICIENT
```

but sufficiency does not establish statistical significance, prediction, causality, effectiveness, or market representativeness.

## Descriptive Statistics

For eligible outcomes Sprint 16 can report:

```text
count
mean_price_change_fraction
median_price_change_fraction
minimum_price_change_fraction
maximum_price_change_fraction
sample_standard_deviation
positive_movement_count
negative_movement_count
zero_movement_count
```

These describe historical raw price movement only.

## Uncertainty

Canonical v1:

```text
SAMPLE_STANDARD_ERROR
SEM = sample_standard_deviation / sqrt(sample_size)
```

For one observation, sample standard deviation and SEM are unavailable.

Confidence intervals are not invented because the protocol does not yet specify an interval method or confidence level.

## Claim Boundary

Under:

```text
DESCRIPTIVE_ONLY
```

even a sufficient sample does not permit:

```text
comparative superiority
predictive claims
causal claims
recommendation-effectiveness claims
success probability
```

An insufficient sample additionally withholds descriptive research conclusions while preserving observations, coverage, and sample shortfall as visible diagnostics.

## Population / Bias Guardrails

Research population metadata records the actual query/filter boundary and candidate count.

Canonical selection basis:

```text
ARCHIVED_OBSERVATIONS
```

Outputs warn that archived recommendations are not automatically an unbiased or representative market population.

Prefiltered research additionally states that statistics apply only to the requested subset.

## Persistence Status

Sprint 16 introduced no outcome/research persistence requirement.

```text
History schema target = 2
outcome observations = on demand
research results = on demand
research population metadata = derived
```

No History schema v3 was introduced.

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
- no portfolio-performance wording for raw price movement;
- explicit population-selection warnings;
- explicit sample-size boundary;
- CLI remains composition/rendering only.

## Testing Status

Sprint 16 includes focused tests for protocol, eligibility, cohorts, coverage, sufficiency, descriptive statistics, uncertainty, claim boundary, research orchestration, population metadata, CLI, and multi-observation E2E.

The corrected multi-observation E2E fixture avoids overlapping candle timestamps and verifies:

```text
3 COMPLETE
1 PARTIAL
1 NOT_MATURE
```

with deterministic eligible movements:

```text
+10%
-5%
0%
```

Final repository closure still requires the full regression suite after this documentation package is applied.

## Deferred Capabilities

Not implemented:

- success/failure labels;
- hit rate / win rate;
- recommendation-effectiveness scoring;
- predictive confidence calibration;
- inferential confidence intervals;
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

Do not infer that the research foundation itself proves recommendation effectiveness.

A future milestone may define inferential or comparative research only after specifying a versioned estimand, comparison semantics, uncertainty/test methodology, population assumptions, multiple-comparison rules, and non-causal/causal interpretation boundaries.
