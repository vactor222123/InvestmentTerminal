# Sprint 16 Plan — Statistically Honest Outcome Research Foundation

**Sprint:** 16  
**Status:** Planned  
**Theme:** Statistically Honest Outcome Research Foundation  
**Depends on:** Sprint 15 — Historical Outcome Methodology Hardening

---

# 1. Sprint Goal

Create the research-policy layer required to summarize historical recommendation outcomes without overstating what the available evidence proves.

Sprint 15 made outcome methodology explicit.

Sprint 16 must make the **research question** explicit.

The sprint will define:

```text
Which observations are eligible?
Which observations belong in the same cohort?
How much evidence is enough to report?
How is missing evidence represented?
What uncertainty must accompany a statistic?
What claims are allowed?
```

Sprint 16 is not a predictive-confidence sprint.

---

# 2. Core Principle

A historical statistic is valid only relative to an explicit research protocol.

Canonical flow:

```text
methodology-aware historical observations
        ↓
HistoricalOutcomeResearchProtocol
        ↓
eligibility assessment
        ↓
cohort identity
        ↓
sample sufficiency assessment
        ↓
descriptive statistics + uncertainty
        ↓
research report with explicit claim boundaries
```

The system must prefer:

```text
INSUFFICIENT_EVIDENCE
```

over a precise-looking but weak statistic.

---

# 3. Canonical Research Vocabulary

Sprint 16 should introduce immutable models for concepts such as:

```text
HistoricalOutcomeResearchProtocol
HistoricalOutcomeCohortKey
HistoricalOutcomeEligibilityAssessment
HistoricalOutcomeSampleAssessment
HistoricalOutcomeResearchSummary
HistoricalOutcomeUncertaintySummary
HistoricalOutcomeResearchWarning
```

Exact names may change during implementation, but the concepts must remain separate.

---

# 4. Research Protocol Identity

## Task 1 — Versioned Research Protocol Model

Add a canonical immutable protocol identity.

Required fields should include at least:

```text
protocol_id
version
allowed_methodology_identities
eligible_statuses
minimum_complete_sample_size
grouping dimensions
missing-evidence policy
uncertainty policy
claim policy
```

The protocol must have a stable identity such as:

```text
DESCRIPTIVE_OUTCOME_RESEARCH@1
```

Rules:

- protocol identity is immutable;
- version changes when research semantics change;
- protocol must serialize deterministically;
- methodology identity remains separate from research-protocol identity.

Tests:

- validation;
- stable identity;
- deterministic serialization;
- version distinction.

---

# 5. Eligibility Policy

## Task 2 — Observation Eligibility Assessment

Create an explicit service that classifies whether an observation is eligible for a research sample.

Initial v1 rule:

```text
COMPLETE
→ eligible for price-movement statistics

PARTIAL
UNAVAILABLE
NOT_MATURE
→ not eligible for price-movement statistics
  but must remain visible in coverage accounting
```

Output must preserve the exclusion reason.

Example reasons:

```text
ELIGIBLE
STATUS_PARTIAL
STATUS_UNAVAILABLE
STATUS_NOT_MATURE
METHODOLOGY_NOT_ALLOWED
INVALID_RESEARCH_INPUT
```

Do not silently drop excluded observations.

Tests:

- each status;
- methodology not allowed;
- deterministic exclusion reason;
- no mutation.

---

# 6. Cohort Identity

## Task 3 — Exact Research Cohort Model

Define a stable cohort key.

Initial grouping dimensions should be explicit and configurable.

At minimum support:

```text
methodology.identity_key
window.kind
window.value
```

Optional protocol-selected dimensions:

```text
recommendation_key
symbol
action
```

Critical rule:

```text
different methodology identity
→ never same research cohort
```

No `PARTIALLY_COMPATIBLE` methodology merging in v1.

Tests:

- stable cohort identity;
- deterministic ordering;
- different methodology version → different cohort;
- different window → different cohort;
- configured action/symbol grouping.

---

# 7. Coverage Accounting

## Task 4 — Research Coverage Summary

Create coverage accounting that includes all candidate observations, not only complete ones.

Required counts:

```text
candidate_count
eligible_count
complete_count
partial_count
unavailable_count
not_mature_count
excluded_count
coverage_fraction
```

Canonical coverage:

```text
eligible COMPLETE observations
/
all candidate observations in the cohort
```

Coverage must not be called success rate.

Tests:

- mixed statuses;
- zero candidates;
- exact fractions;
- excluded methodology/input cases.

---

# 8. Minimum Sample Size

## Task 5 — Sample Sufficiency Policy

Introduce an explicit minimum-sample rule.

Initial default should be conservative and configurable through the research protocol.

Example state model:

```text
INSUFFICIENT
SUFFICIENT
```

The implementation must not invent a universal statistically optimal threshold.

Instead:

```text
minimum_complete_sample_size
```

is a protocol parameter.

When insufficient:

- coverage may still be reported;
- counts may still be reported;
- raw observations remain available;
- inferential/effectiveness-like conclusions are prohibited;
- descriptive movement summary may be withheld or clearly marked exploratory according to protocol.

Tests:

- below threshold;
- exactly threshold;
- above threshold;
- invalid threshold.

---

# 9. Descriptive Statistics

## Task 6 — Research Descriptive Summary

For sufficient eligible observations, calculate transparent descriptive statistics.

Initial v1 candidates:

```text
count
mean
median
minimum
maximum
standard deviation
positive-movement count
negative-movement count
zero-movement count
```

Important:

```text
positive movement != successful recommendation
negative movement != failed recommendation
```

Do not introduce:

```text
hit rate
win rate
accuracy
effectiveness score
```

unless a later explicit label policy defines what those words mean.

Tests:

- deterministic values;
- single observation;
- mixed positive/negative/zero;
- no NaN/Infinity serialization.

---

# 10. Uncertainty

## Task 7 — Uncertainty Reporting Foundation

Add explicit uncertainty output.

Sprint 16 v1 should prefer a simple, transparent, well-tested method over sophisticated inference.

Recommended initial boundary:

```text
sample standard deviation
standard error of the mean
optional confidence interval only if the protocol explicitly enables it
```

If confidence intervals are implemented, the method and level must be explicit in the protocol/output.

Example:

```text
method = "NORMAL_APPROXIMATION"
confidence_level = 0.95
```

If assumptions are not satisfied or sample is insufficient:

```text
interval = None
warning = explicit
```

No predictive confidence language.

Tests:

- insufficient sample;
- deterministic interval calculation;
- confidence level validation;
- zero variance;
- serialization.

---

# 11. Claim Policy

## Task 8 — Research Claim Boundary

Create a small explicit claim-policy model/service.

Allowed Sprint 16 wording:

```text
descriptive historical price movement
historical sample coverage
sample uncertainty
```

Disallowed without future methodology:

```text
recommendation was successful
recommendation accuracy
strategy effectiveness
predictive confidence
causal effect
expected future return
```

The service should expose machine-readable claim capability, for example:

```text
DESCRIPTIVE_ONLY
```

and warnings suitable for CLI/report output.

Tests:

- allowed claim category;
- prohibited effectiveness language;
- deterministic warnings.

---

# 12. Research Aggregation Service

## Task 9 — Protocol-Aware Research Service

Compose:

```text
observations
+ research protocol
→ eligibility
→ cohorts
→ coverage
→ sufficiency
→ descriptive statistics
→ uncertainty
→ claim boundary
```

Critical rules:

- no mixed methodology identities;
- no silent excluded observations;
- no statistic without sample metadata;
- no effect/causal interpretation;
- deterministic cohort ordering;
- pure/in-memory computation.

Tests:

- multiple cohorts;
- insufficient cohort;
- sufficient cohort;
- missing evidence;
- mixed methodologies;
- deterministic output.

---

# 13. Selection and Survivorship Guardrails

## Task 10 — Research Population Metadata

Sprint 16 cannot fully solve survivorship bias without a broader historical universe model.

It can, however, prevent silent ambiguity.

Research output should carry explicit population metadata such as:

```text
selection_basis
requested_recommendation_key
requested_symbol
requested_action
origin_start
origin_end
candidate_count
```

If the population was prefiltered, the report must say so.

Add warnings that the sample reflects archived recommendations available to the system and is not automatically an unbiased market population.

Tests:

- filtered population metadata;
- unfiltered metadata;
- deterministic warnings.

---

# 14. CLI

## Task 11 — Research Summary CLI

Add a read-only research CLI.

Inputs should include:

```text
history database
market database
recommendation key / optional filters
methodology
window
as_of
research protocol / minimum sample size
session calendar when required
```

Output must show:

```text
protocol identity
methodology identity
cohort identity
candidate count
eligible count
coverage
sample sufficiency
descriptive statistics
uncertainty
claim boundary
warnings
```

JSON mode must preserve all semantics.

The CLI must not contain research math.

Tests:

- argument validation;
- insufficient sample output;
- sufficient sample output;
- JSON serialization;
- session-aware methodology;
- claim warning presence.

---

# 15. Realistic E2E Fixture

## Task 12 — Multi-Observation Research E2E

Build a deterministic fixture containing multiple historical recommendation origins.

Include:

```text
COMPLETE observations
PARTIAL observation
NOT_MATURE observation
positive raw movement
negative raw movement
zero/raw-flat movement if useful
```

Run:

```text
historical states
→ methodology-aware outcomes
→ research protocol
→ cohort
→ coverage
→ sufficiency
→ descriptive summary
→ uncertainty
→ CLI/JSON-ready report
```

Verify:

- excluded observations remain counted;
- methodology identity is preserved;
- no mixed cohort;
- sample threshold behavior;
- no success/effectiveness wording;
- deterministic statistics;
- no persistence.

---

# 16. Documentation and Review

## Task 13 — Sprint 16 Review

Update:

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/SPRINT_16_PLAN.md
docs/SPRINT_16_REVIEW.md
```

Document:

- protocol semantics;
- cohort semantics;
- sample-size policy;
- missing-evidence treatment;
- uncertainty method;
- selection/survivorship limitations;
- claim boundary;
- deferred effectiveness scoring.

---

# 17. Explicit Non-Goals

Sprint 16 must not implement:

- recommendation success/failure labels;
- hit rate;
- win rate;
- recommendation accuracy;
- recommendation-effectiveness score;
- predictive confidence calibration;
- causal inference;
- factor causal attribution;
- automated strategy optimization;
- backtest trading simulation;
- transaction-cost modeling;
- dividend-adjusted total return;
- FX-adjusted return;
- portfolio-performance attribution;
- outcome persistence;
- Knowledge Domain;
- autonomous trading;
- broker execution.

---

# 18. Statistical Honesty Rules

The following are architectural requirements.

## Rule 1 — Every statistic has a denominator

Never report a movement statistic without sample count.

## Rule 2 — Missing evidence stays visible

`PARTIAL`, `UNAVAILABLE`, and `NOT_MATURE` are coverage facts.

They must not disappear from the research report.

## Rule 3 — Methodologies are not silently pooled

Different exact methodology identities remain separate.

## Rule 4 — Small samples are explicit

A small sample is not upgraded into a confident conclusion.

## Rule 5 — Descriptive is not predictive

Historical mean movement does not imply expected future return.

## Rule 6 — Correlation is not causation

No causal wording is allowed.

## Rule 7 — Positive movement is not automatically success

Success requires a future explicit recommendation-label policy.

## Rule 8 — Research protocol is versioned

Changing sample or uncertainty semantics requires a new protocol version.

---

# 19. Persistence Decision

Default Sprint 16 decision:

```text
research summaries = derived/on demand
research protocol = code/config identity
History schema target = 2
```

Do not add schema v3 unless implementation reveals a concrete requirement that cannot be satisfied by deterministic reconstruction.

---

# 20. Acceptance Criteria

Sprint 16 is complete when:

```text
[ ] versioned research protocol exists
[ ] observation eligibility is explicit
[ ] excluded observations retain reasons
[ ] exact research cohort identity exists
[ ] different methodologies are never silently pooled
[ ] coverage includes incomplete observations
[ ] minimum sample size is explicit/configurable
[ ] sample sufficiency is machine-readable
[ ] descriptive statistics are transparent
[ ] uncertainty output is explicit
[ ] claim boundary is machine-readable
[ ] population/selection metadata is visible
[ ] protocol-aware research service exists
[ ] read-only research CLI exists
[ ] realistic multi-observation E2E exists
[ ] no effectiveness/confidence/causal metric is introduced
[ ] no outcome/research persistence is introduced without justification
[ ] full regression suite passes
[ ] documentation is reconciled
```

---

# 21. Recommended Implementation Order

```text
1. Research protocol model
2. Eligibility policy
3. Cohort identity
4. Coverage summary
5. Sample sufficiency
6. Descriptive statistics
7. Uncertainty
8. Claim boundary
9. Protocol-aware research service
10. Population metadata / bias warnings
11. Research CLI
12. Realistic E2E
13. Documentation + review
```

---

# 22. Sprint Statement

> Sprint 15 made historical outcome methodology explicit. Sprint 16 makes the rules for learning from those outcomes explicit, so the system can report evidence without pretending that a small or selected historical sample proves recommendation effectiveness.
