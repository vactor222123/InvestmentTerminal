# Sprint 17 Plan — Research Provenance and Population Quality Hardening

**Sprint:** 17  
**Status:** Implemented — final verification pending  
**Theme:** Research Provenance and Population Quality Hardening  
**Depends on:** Sprint 16 — Statistically Honest Outcome Research Foundation

---

# 1. Sprint Goal

Strengthen the population and source-evidence boundary around descriptive historical outcome research before considering any inferential, comparative, hit-rate, effectiveness, or predictive-confidence work.

Sprint 17 makes research provenance explicit from source snapshot lifecycle through temporal coverage and query selection while preserving the descriptive-only claim boundary from Sprint 16.

# 2. Delivered Architecture

```text
source snapshots
        ↓
import lifecycle quality
        ↓
methodology-aware source observations
        ↓
temporal completeness
        ↓
population frame
        ↓
selection accounting
        ↓
selected candidates
        ↓
eligibility + coverage
        ↓
HistoricalOutcomeResearchProvenanceSummary
        ↓
HistoricalOutcomeResearchCohortResult
        ↓
read-only research CLI
```

# 3. Delivered Tasks

## Task 1 — Population Frame Contract — DONE

Delivered canonical pre-selection and post-selection denominator contract:

```text
source_observation_count
selected_candidate_count
excluded_by_selection_count
selection_fraction
selection_applied
```

## Task 2 — Selection Provenance Integration — DONE

Integrated population frame into research orchestration and result serialization.

`source_observation_count` became explicit for callers that know the pre-selection denominator.

## Task 3 — CLI Population Frame Integration — DONE

CLI now forwards produced-observation count into research orchestration and exposes source-to-selected denominators.

## Task 4 — Selection Reason Accounting — DONE

Delivered non-exclusive query exclusion-reason accounting for all canonical query predicates.

One observation may contribute to multiple reason counts.

## Task 5 — Selection Accounting Integration — DONE

Integrated source-result-aware selection accounting into research orchestration and CLI.

Research does not infer reasons from counts alone.

## Task 6 — Population Completeness Assessment — DONE

Delivered temporal-boundary completeness contract:

```text
UNKNOWN
PARTIAL
COVERED
```

Internal archive continuity remains `NOT_ASSESSED` because the product has no canonical expected snapshot cadence.

## Task 7 — Completeness Integration — DONE

Integrated temporal completeness into the research result and CLI using pre-selection source observations and query origin boundaries.

## Task 8 — Source Import Quality Assessment — DONE

Delivered unique-snapshot import-lifecycle quality assessment:

```text
UNKNOWN
PARTIAL
COMPLETE
```

Only canonical `IMPORTED` lifecycle state counts as imported.

## Task 9 — Source Import Quality Integration — DONE

Integrated import-quality assessment through the application/CLI boundary while keeping the research service persistence-agnostic.

## Task 10 — Research Provenance Summary Contract — DONE

Delivered immutable:

```text
HistoricalOutcomeResearchProvenanceSummary
```

over:

```text
SOURCE_IMPORT_QUALITY
POPULATION_COMPLETENESS
POPULATION_FRAME
SELECTION_ACCOUNTING
```

No overall quality score was introduced.

## Task 11 — Provenance Summary Integration — DONE

Made `provenance` the canonical result boundary.

Compatibility was preserved through read-only Python properties and transitional serialization aliases for pre-provenance consumers.

## Task 12 — Provenance E2E — DONE

Delivered production-style end-to-end coverage across History SQLite, import lifecycle, local market SQLite, methodology-aware observations, query selection, provenance, and descriptive research result.

## Task 13 — Documentation and Final Review — IN PROGRESS

This package reconciles:

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/SPRINT_17_PLAN.md
docs/SPRINT_17_REVIEW.md
```

Final repository verification remains after applying the package.

# 4. Architecture Guardrails Preserved

- research remains derived/on demand;
- History schema remains version 2;
- no provenance/research persistence;
- research service remains persistence-agnostic;
- import-state repository remains at application/CLI boundary;
- no hidden archive-cadence assumption;
- no hidden archive-continuity claim;
- no hidden population-representativeness assumption;
- no exclusive-reason assumption for selection diagnostics;
- no overall provenance quality score;
- no hit rate;
- no success/failure label;
- no recommendation-effectiveness score;
- no predictive confidence;
- no causal inference;
- CLI remains composition/rendering only.

# 5. Explicit Non-Goals

Sprint 17 did not implement:

- recommendation effectiveness;
- success probability;
- hit/win rate;
- predictive calibration;
- causal attribution;
- inferential hypothesis tests;
- confidence intervals;
- multiple-comparison inference;
- expected archive cadence;
- archive gap detection;
- target-population representativeness model;
- total return;
- FX normalization;
- portfolio attribution;
- outcome/research persistence;
- autonomous trading;
- broker execution;
- Knowledge Domain.

# 6. Persistence Decision

```text
History schema target = 2
outcome observations = derived/on demand
research provenance = derived/on demand
research results = derived/on demand
```

No schema v3 was justified.

# 7. Compatibility Decision

`provenance` is the canonical new result boundary.

During the migration window:

```text
result.population_frame
result.selection_accounting
result.population_completeness
result.source_import_quality
```

remain read-only compatibility properties.

Likewise the serialized result retains transitional top-level aliases while canonical consumers should use:

```text
payload["provenance"]
```

Removing aliases requires a dedicated breaking-contract migration.

# 8. Final Verification

After applying Task 13 docs:

```powershell
git diff --check
python -m pytest -q
git status --short
```

Sprint 17 is complete when documentation is committed/pushed, the full regression suite is green, and the working tree is clean.

# 9. Sprint Statement

> Sprint 17 did not make historical research more confident. It made the system more explicit about where the research population came from, how complete its source boundaries are, which source snapshots completed import, what selection removed, and which provenance claims the system still cannot make.
