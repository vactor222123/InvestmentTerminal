# Sprint 16 Review — Statistically Honest Outcome Research Foundation

**Sprint:** 16  
**Status:** Implementation Complete — Final Repository Verification Pending  
**Theme:** Statistically Honest Outcome Research Foundation  
**Implementation baseline before final documentation:** `f411994`

---

# 1. Executive Summary

Sprint 16 achieved its goal: Investment Terminal now has a versioned descriptive research protocol over methodology-aware historical outcome observations.

The key architecture is:

```text
historical observations
→ explicit protocol
→ exact cohorts
→ visible eligibility/coverage
→ sample sufficiency
→ descriptive statistics
→ uncertainty
→ claim boundary
→ population/bias metadata
→ read-only result
```

This is deliberately not an effectiveness model.

# 2. Major Delivered Contracts

Sprint 16 delivered canonical contracts for:

```text
research protocol
eligibility
cohort identity
coverage
sample sufficiency
descriptive summary
uncertainty
claim permissions
population metadata
research orchestration
```

The CLI renders these contracts rather than implementing parallel statistical logic.

# 3. Statistical Honesty Review

## 3.1 Eligibility

Only protocol-eligible observations enter descriptive statistics.

Incomplete observations remain visible in coverage rather than disappearing from the denominator.

## 3.2 Cohort Integrity

Exact methodology identity and observation-window semantics are not silently pooled.

This prevents descriptive results from combining observations that answer different historical questions.

## 3.3 Sample Size

`SUFFICIENT` means only:

```text
eligible_sample_size >= protocol.minimum_complete_sample_size
```

It does not mean statistically significant, predictive, causal, effective, or representative.

## 3.4 Descriptive Statistics

The implemented statistics describe `price_change_fraction` only.

Positive movement is not called a win or success.

## 3.5 Uncertainty

Sprint 16 reports sample standard deviation and standard error.

It intentionally does not fabricate a 95% confidence interval because no interval method or confidence level is defined by the current protocol.

## 3.6 Claim Boundary

`DESCRIPTIVE_ONLY` remains enforced even for large sufficient samples.

The model explicitly denies predictive, causal, comparative-superiority, and effectiveness claims.

## 3.7 Population Selection

Research metadata states that the population consists of archived observations and records the actual query/filter boundary.

The output warns that this is not automatically an unbiased or representative market population.

# 4. Architecture Review

## 4.1 Source-of-Truth Hierarchy

```text
Archived Review Package
→ canonical historical recommendation evidence

History SQLite
→ rebuildable normalized projection

Local candle DB
→ persisted market evidence

Explicit session calendar
→ methodology input

Outcome observation
→ rebuildable derived result

Research result
→ rebuildable derived descriptive result
```

No derived research result became canonical history.

## 4.2 Persistence

No History migration was required.

```text
History schema target = 2
```

No outcome/research tables are introduced.

## 4.3 CLI Boundary

The research CLI composes existing services and renders human/JSON output.

It does not own:

- eligibility rules;
- cohort grouping;
- coverage math;
- sample sufficiency;
- descriptive math;
- uncertainty math;
- claim permissions.

# 5. E2E Review

The final multi-observation fixture uses non-overlapping exact candle timestamps and verifies:

```text
COMPLETE +10%
COMPLETE -5%
COMPLETE 0%
PARTIAL
NOT_MATURE
```

It proves that the integrated pipeline preserves evidence state, computes only from eligible observations, reports sample sufficiency and uncertainty, keeps claim restrictions, serializes to JSON, and creates no research/outcome persistence.

# 6. Guardrails Preserved

- no hindsight leakage;
- no present-price fallback;
- no hidden nearest evidence;
- no implicit session calendar;
- no mixed-methodology research cohort;
- no hidden removal of incomplete evidence from coverage;
- no representativeness assumption;
- no invented confidence interval;
- no hit rate;
- no success/failure scoring;
- no effectiveness scoring;
- no predictive confidence;
- no causal claim;
- no raw-price-to-portfolio-performance reinterpretation.

# 7. Remaining Risks

The main remaining limitations are intentionally visible:

- archived recommendations may be selected/non-representative;
- samples may be small;
- raw close-price movement is not total return;
- current uncertainty is descriptive and does not provide an inferential interval;
- no comparison/control estimand exists;
- no multiple-comparison methodology exists;
- no causal design exists.

These are reasons not to over-interpret the current research output, not reasons to weaken the guardrails.

# 8. Acceptance Checklist

Implementation:

```text
[x] versioned research protocol
[x] explicit eligibility
[x] exact cohort grouping
[x] visible coverage
[x] minimum sample-size assessment
[x] descriptive statistics
[x] sample standard error
[x] explicit no-CI behavior
[x] descriptive-only claim boundary
[x] protocol-aware orchestration
[x] population/bias metadata
[x] read-only research CLI
[x] deterministic multi-observation E2E
[x] no research/outcome persistence
[x] History schema remains version 2
[x] Sprint 16 review exists
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

Do not automatically implement hit rate or predictive confidence.

The next sprint should first choose one of two paths:

1. remain descriptive and improve evidence/population quality; or
2. define a new versioned inferential/comparative protocol with an explicit estimand, population assumptions, comparison semantics, interval/test methodology, multiple-comparison discipline, and claim vocabulary.

Knowledge Domain work should also continue to respect methodology identity, sample sufficiency, provenance, uncertainty, and claim boundaries.

# 10. Final Assessment

Sprint 16 converts the project's previous warning — “define a statistically honest protocol before effectiveness metrics” — into executable architecture.

The most important outcome is not the mean or standard error calculation.

It is that the system now knows, in machine-readable form, when evidence is eligible, what was excluded, whether the sample threshold is met, what uncertainty can be reported, how the population was selected, and which claims remain forbidden.
