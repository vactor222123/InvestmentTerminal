# Sprint 16 Plan — Statistically Honest Outcome Research Foundation

**Sprint:** 16  
**Status:** Implemented — final verification pending  
**Theme:** Statistically Honest Outcome Research Foundation  
**Depends on:** Sprint 15 — Historical Outcome Methodology Hardening

---

# 1. Sprint Goal

Establish an explicit, reproducible, statistically honest research boundary for historical recommendation outcomes before introducing effectiveness, hit-rate, predictive-confidence, or causal claims.

Sprint 16 turns methodology-aware observations into protocol-aware descriptive research while preserving incomplete evidence, sample limitations, population-selection warnings, and non-causal interpretation.

# 2. Delivered Architecture

```text
HistoricalMethodologyAwareObservationResult
        +
HistoricalOutcomeResearchProtocol
        ↓
exact research cohorts
        ↓
eligibility + coverage
        ↓
sample sufficiency
        ↓
descriptive statistics
        ↓
uncertainty
        ↓
claim boundary
        ↓
population metadata
        ↓
HistoricalOutcomeResearchCohortResult
        ↓
read-only research CLI
```

# 3. Delivered Tasks

## Task 1 — Research Protocol Foundation — DONE

Delivered canonical versioned research protocol with explicit methodology eligibility, eligible statuses, minimum sample size, grouping dimensions, missing-evidence policy, uncertainty policy, and claim policy.

Canonical v1:

```text
DESCRIPTIVE_OUTCOME_RESEARCH@1
```

## Task 2 — Research Eligibility — DONE

Eligibility is explicit and protocol-aware. Only allowed methodology identities and eligible observation statuses can enter the descriptive sample.

## Task 3 — Exact Research Cohorts — DONE

Cohorts are separated by canonical grouping dimensions:

```text
METHODOLOGY_IDENTITY
WINDOW_KIND
WINDOW_VALUE
```

No silent cross-methodology or cross-window pooling.

## Task 4 — Coverage Accounting — DONE

Coverage preserves candidate denominator and explicit counts for COMPLETE, PARTIAL, UNAVAILABLE, NOT_MATURE, eligible, and excluded observations.

## Task 5 — Sample Sufficiency — DONE

Delivered explicit:

```text
SUFFICIENT
INSUFFICIENT
```

against the protocol's minimum eligible sample size.

Sufficiency is a protocol threshold only, not statistical significance.

## Task 6 — Descriptive Statistics — DONE

Delivered raw price-movement descriptive statistics including count, mean, median, min/max, sample standard deviation, and positive/negative/zero movement counts.

No hit rate, win rate, or effectiveness metric.

## Task 7 — Uncertainty Reporting — DONE

Delivered:

```text
SAMPLE_STANDARD_ERROR
```

with sample standard deviation and standard error of the mean.

Confidence intervals remain absent until a future protocol explicitly defines interval method and confidence level.

## Task 8 — Research Claim Boundary — DONE

Delivered machine-readable `DESCRIPTIVE_ONLY` claim permissions.

Predictive, causal, comparative-superiority, and recommendation-effectiveness claims remain forbidden regardless of sample size.

Insufficient samples additionally withhold descriptive research conclusions.

## Task 9 — Protocol-Aware Research Service — DONE

Delivered orchestration across cohorts, coverage, sufficiency, eligible outcomes, descriptive statistics, uncertainty, and claim boundary without duplicating domain logic.

## Task 10 — Population Metadata / Bias Guardrails — DONE

Delivered explicit selection metadata from `HistoricalOutcomeQuery`, candidate denominator, archived-observation selection basis, prefilter visibility, and representative-population warnings.

## Task 11 — Research Summary CLI — DONE

Delivered read-only `outcome_research` CLI.

CLI exposes protocol, methodology, query, population, cohort, coverage, sample sufficiency, descriptive statistics, uncertainty, claims, and warnings.

CLI owns no research math and no persistence.

## Task 12 — Multi-Observation Research E2E — DONE

Delivered deterministic production-style E2E with local SQLite candle evidence and methodology-aware observations:

```text
3 COMPLETE
1 PARTIAL
1 NOT_MATURE
```

Eligible movements:

```text
+10%
-5%
0%
```

The fixture verifies coverage, sufficiency, descriptive statistics, uncertainty, claim boundary, JSON serialization, bias warnings, and absence of outcome/research persistence.

## Task 13 — Documentation and Final Review — IN PROGRESS

This package reconciles:

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/SPRINT_16_PLAN.md
docs/SPRINT_16_REVIEW.md
```

Final repository verification remains after applying the package.

# 4. Architecture Guardrails Preserved

- research is derived/on demand;
- History schema remains version 2;
- no outcome/research persistence;
- no hidden methodology pooling;
- no missing-evidence deletion from coverage;
- no hidden population representativeness assumption;
- no invented confidence interval;
- no hit rate;
- no success/failure label;
- no recommendation-effectiveness score;
- no predictive confidence;
- no causal inference;
- no portfolio-performance reinterpretation;
- CLI remains composition/rendering only.

# 5. Explicit Non-Goals

Sprint 16 did not implement:

- recommendation effectiveness;
- success probability;
- hit/win rate;
- predictive calibration;
- causal attribution;
- inferential hypothesis tests;
- confidence intervals without an explicit policy;
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
research results = derived/on demand
research population metadata = derived
```

No schema v3 was justified.

# 7. Final Verification

After applying Task 13 docs:

```powershell
git diff --check
python -m pytest -q
git status --short
```

Sprint 16 is complete when documentation is committed/pushed, the full regression suite is green, and the working tree is clean.

# 8. Sprint Statement

> Sprint 16 did not teach Investment Terminal to declare recommendations successful. It taught the system how to describe historical outcome evidence under an explicit protocol while making sample limits, uncertainty, selection bias, and claim boundaries visible.
