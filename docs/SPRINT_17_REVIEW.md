# Sprint 17 Review — Research Provenance and Population Quality Hardening

**Sprint:** 17  
**Status:** Implementation Complete — Final Repository Verification Pending  
**Theme:** Research Provenance and Population Quality Hardening  
**Implementation baseline before final documentation:** `58834f6`

---

# 1. Executive Summary

Sprint 17 achieved its goal: Investment Terminal now has an explicit, machine-readable provenance boundary around descriptive historical outcome research.

The key architecture is:

```text
source snapshot lifecycle
→ source observation population
→ temporal completeness
→ population frame
→ selection reasons
→ selected candidates
→ eligibility/coverage
→ descriptive research
→ provenance envelope
```

This is deliberately not an inferential or effectiveness model.

# 2. Major Delivered Contracts

Sprint 17 delivered canonical contracts for:

```text
research population frame
selection-reason accounting
temporal population completeness
source import quality
research provenance summary
provenance-aware research orchestration
provenance-aware CLI
compatibility migration
provenance E2E
```

# 3. Population and Provenance Honesty Review

## 3.1 Population Denominator

Research can now distinguish:

```text
source observations
selected candidates
excluded by selection
```

instead of exposing only the post-query candidate count.

This makes the source-to-selected denominator visible without claiming that the source archive represents a broader market universe.

## 3.2 Selection Reasons

Selection diagnostics are explicit for each active query predicate.

Reason counts are deliberately non-exclusive.

A single observation can fail multiple predicates, so diagnostic reason failures are not equated with the excluded-observation count.

## 3.3 Temporal Completeness

Sprint 17 assesses whether observed source timestamps span an explicitly requested origin interval.

Canonical statuses are:

```text
UNKNOWN
PARTIAL
COVERED
```

The contract intentionally does not infer internal archive continuity.

Because no canonical expected snapshot cadence exists:

```text
internal_continuity_status = NOT_ASSESSED
```

This prevents “boundary coverage” from being misreported as “no missing snapshots”.

## 3.4 Source Import Quality

Source import quality is evaluated over unique source snapshot IDs.

Canonical statuses are:

```text
UNKNOWN
PARTIAL
COMPLETE
```

`COMPLETE` requires all unique source snapshots to have canonical `IMPORTED` lifecycle state.

This is an ingestion-provenance statement only.

It is not a representativeness, statistical-validity, or research-quality score.

## 3.5 Provenance Summary

Sprint 17 introduced:

```text
HistoricalOutcomeResearchProvenanceSummary
```

as the single canonical envelope for:

```text
SOURCE_IMPORT_QUALITY
POPULATION_COMPLETENESS
POPULATION_FRAME
SELECTION_ACCOUNTING
```

The summary reports component availability but deliberately does not collapse them into one score.

`complete_component_set = true` means only that all four provenance components are present.

## 3.6 Compatibility

Task 11 initially exposed an important migration risk: replacing top-level provenance fields directly would break existing Python and serialization consumers.

The final implementation therefore preserves:

- canonical `provenance` for new consumers;
- read-only compatibility properties for old Python consumers;
- transitional top-level serialization aliases;
- legacy CLI fixture rendering fallback.

This allows the boundary to migrate without silently breaking the existing regression contract.

# 4. Architecture Review

## 4.1 Persistence Boundary

The research service remains persistence-agnostic.

It does not open History SQLite or instantiate import-state repositories.

Application/CLI composition reads canonical import state and passes an immutable assessment into research orchestration.

## 4.2 Source-of-Truth Hierarchy

```text
Archived Review Package
→ canonical historical recommendation evidence

History SQLite
→ rebuildable normalized historical projection

Historical import lifecycle
→ canonical source-ingestion provenance

Local candle DB
→ persisted market evidence

Methodology-aware observation
→ rebuildable derived outcome evidence

Research provenance summary
→ rebuildable source/population provenance

Research result
→ rebuildable descriptive research result
```

No derived provenance or research result became canonical history.

## 4.3 Persistence

No History migration was required.

```text
History schema target = 2
```

No outcome, provenance, or research tables were introduced.

## 4.4 CLI Boundary

The research CLI composes repositories/services and renders human/JSON output.

It does not own:

- import-quality rules;
- temporal completeness semantics;
- population-frame arithmetic;
- selection-reason semantics;
- eligibility rules;
- coverage math;
- descriptive math;
- uncertainty math;
- claim permissions.

# 5. E2E Review

The Sprint 17 provenance E2E uses:

```text
History SQLite
local market SQLite
3 archived snapshots
3 methodology-aware source observations
```

Import lifecycle:

```text
2 IMPORTED
1 METADATA_ONLY
```

Research query selects one source observation inside the requested temporal interval.

The E2E verifies:

```text
source import quality = PARTIAL
temporal completeness = COVERED
source observations = 3
selected candidates = 1
selection fraction = 1/3
selection reasons = ORIGIN_FROM + ORIGIN_TO
eligible sample = 1
sample sufficiency = SUFFICIENT
claim policy = DESCRIPTIVE_ONLY
```

It also verifies canonical provenance serialization and compatibility aliases.

# 6. Guardrails Preserved

- no hindsight leakage;
- no current-price fallback;
- no hidden nearest evidence;
- no implicit session calendar;
- no hidden source denominator;
- no exclusive selection-reason assumption;
- no hidden archive-continuity inference;
- no population-representativeness assumption;
- no provenance quality score;
- no hit rate;
- no success/failure scoring;
- no effectiveness scoring;
- no predictive confidence;
- no causal claim;
- no outcome/provenance/research persistence.

# 7. Remaining Risks

The main remaining limitations are intentionally visible:

- archived recommendations may still be selected/non-representative;
- no explicit expected archive cadence exists;
- internal archive gaps cannot yet be assessed canonically;
- `IMPORTED` means ingestion lifecycle completeness, not semantic completeness;
- temporal `COVERED` means requested boundary coverage only;
- raw close-price movement remains not total return;
- no comparison/control estimand exists;
- no interval/test methodology exists;
- no multiple-comparison methodology exists;
- no causal design exists.

These are reasons not to over-interpret the research output, not reasons to weaken the provenance guardrails.

# 8. Acceptance Checklist

Implementation:

```text
[x] explicit source population frame
[x] selection provenance integration
[x] CLI denominator visibility
[x] selection-reason accounting
[x] selection-accounting integration
[x] temporal completeness assessment
[x] completeness integration
[x] source import quality assessment
[x] import-quality integration
[x] provenance summary contract
[x] provenance summary integration
[x] compatibility-safe migration
[x] provenance E2E
[x] no provenance/research persistence
[x] History schema remains version 2
[x] Sprint 17 review exists
```

Final repository closure:

```text
[ ] documentation diff passes git diff --check
[ ] full regression suite passes after documentation update
[ ] Task 13 docs committed
[ ] Task 13 pushed to origin/develop
[ ] working tree clean
```

# 9. Recommendation for the Next Sprint

Do not automatically implement hit rate, effectiveness scoring, predictive confidence, or inferential confidence intervals.

The next sprint should first choose a versioned research direction.

A future inferential/comparative protocol would still need:

```text
target estimand
source and target population assumptions
comparison/control semantics
interval/test methodology
multiple-comparison discipline
selection/survivorship treatment
methodology compatibility
claim vocabulary
```

An alternative descriptive path would be to define an explicit expected archive cadence and target-population universe before making stronger population-completeness statements.

# 10. Final Assessment

Sprint 17 converts population and source-evidence caveats into executable provenance architecture.

The most important result is not a new metric.

It is that the system now knows, in machine-readable form, which source snapshots completed import, what temporal boundaries the source frame covers, how many observations were available before selection, why observations were excluded, and which provenance questions remain unresolved.
