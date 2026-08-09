# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 20 — Evidence-Grounded AI Experience Foundation
**Current development branch:** `develop`

## 1. Product Evolution

```text
Foundation
→ Current-State Analysis
→ Portfolio and Decision Intelligence
→ Unified Review Package
→ Historical Intelligence Foundation
→ Historical Comparison and Replay
→ Outcome-Aware Historical Intelligence
→ Historical Outcome Methodology Hardening
→ Statistically Honest Outcome Research Foundation
→ Research Provenance and Population Quality Hardening
→ Explicit Historical Archive Continuity
→ Knowledge Domain Foundation
→ Evidence-Grounded AI Experience Foundation
→ Provider Integration and Operational AI Controls
```

## 2. Completed Milestones

### Sprint 11 — Foundation

Architecture and canonical product documentation foundation.

### Sprint 12 — Historical Intelligence Foundation

Immutable Review Package history, integrity verification, History SQLite, typed imports, and timeline foundation.

### Sprint 13 — Historical Comparison and Replay

Historical navigation, comparison, compatibility, replay, read-only CLIs, migrations/import state, and realistic E2E coverage.

### Sprint 14 — Outcome-Aware Historical Intelligence

Canonical outcome observations, exact local price evidence, raw price movement, descriptive aggregation, CLI, and E2E.

### Sprint 15 — Historical Outcome Methodology Hardening

Explicit methodology identities, deterministic session semantics, exact-only evidence, methodology-aware observations, and CLI/E2E.

### Sprint 16 — Statistically Honest Outcome Research Foundation

`DESCRIPTIVE_OUTCOME_RESEARCH@1`, exact cohorts, eligibility/coverage, sample sufficiency, descriptive statistics, uncertainty, and claim boundaries.

### Sprint 17 — Research Provenance and Population Quality Hardening

Population frame, selection accounting, boundary completeness, source import quality, canonical research provenance, compatibility migration, and E2E.

### Sprint 18 — Explicit Historical Archive Continuity

`FIXED_INTERVAL_ARCHIVE_CADENCE@1`, expected timestamp generation, exact archive-gap assessment, repository composition, internal continuity, optional archive-gap provenance, CLI, and E2E.

### Sprint 19 — Knowledge Domain Foundation

Immutable/versioned Knowledge records, traceable evidence references, Knowledge provenance, separate Knowledge SQLite schema, deterministic projection/query/comparison, read-only CLI, and real E2E.

### Sprint 20 — Evidence-Grounded AI Experience Foundation

Delivered:

- versioned `EVIDENCE_GROUNDED_PROMPT@1` contract;
- versioned `EVIDENCE_GROUNDED_ANSWER@1` contract;
- explicit Knowledge citations for every AI claim;
- exact Knowledge-lineage grounding validation;
- conservative COMPLETE-only v1 grounding admissibility;
- deterministic context selection;
- provider-neutral prompt input;
- provider-independent model adapter boundary;
- static deterministic reference adapter;
- strict JSON response parser;
- fail-closed generation orchestration;
- compact grounded generation audit trace;
- read-only reference CLI;
- real Knowledge SQLite → grounded workflow → CLI E2E.

Canonical grounded AI flow:

```text
KnowledgeRecordEnvelope
→ deterministic context selection
→ EVIDENCE_GROUNDED_PROMPT@1
→ GroundedModelAdapter
→ raw response
→ strict JSON parser
→ EVIDENCE_GROUNDED_ANSWER@1 candidate
→ exact Knowledge grounding validation
→ ADMISSIBLE result
→ audit trace / read-only CLI
```

## 3. Evidence and Authority Hierarchy

```text
Archived Review Package JSON
    canonical historical source evidence

History SQLite
    rebuildable normalized historical projection

Historical outcome/research layers
    rebuildable descriptive historical intelligence

KnowledgeRecord
    versioned, rebuildable, traceable knowledge statement

KnowledgeRecordEnvelope
    Knowledge record + rebuildable provenance assessment

GroundedPromptInput
    deterministic provider-neutral AI input

GroundedModelResponse
    untrusted raw provider output

GroundedAIAnswer candidate
    structurally parsed but not yet trusted

GroundingValidationAssessment
    exact citation/Knowledge admissibility check

ADMISSIBLE GroundedGenerationResult
    final v1 grounded result
```

Raw model output never outranks Knowledge evidence.

## 4. Stable AI Guardrails

Sprint 20 does not establish:

```text
truth scoring
semantic entailment proof
confidence
prediction
recommendation effectiveness
success probability
causal validity
model authority
autonomous action
```

`COMPLETE` Knowledge provenance means checksum-backed canonical snapshot lineage exists. It is not a model-confidence or truth score.

`ADMISSIBLE` means the answer citations exactly resolve to supplied COMPLETE Knowledge context. It does not prove the natural-language claim is semantically entailed or universally true.

## 5. Provider Boundary Status

Current implementation:

```text
GroundedModelAdapter = abstract provider boundary
StaticGroundedModelAdapter = deterministic reference/test implementation
real provider adapter = deferred
```

Not implemented in Sprint 20:

```text
OpenAI SDK
Anthropic SDK
other provider SDKs
HTTP/network transport
API keys/secrets
streaming
retry/rate-limit logic
model/provider allowlists
cost/token accounting
```

## 6. Audit and Persistence Status

```text
History schema target = 2
Knowledge schema target = 1
AI persistence schema = none
AI trace = derived/on demand
```

Grounded generation audit traces are compact derived views and are not persisted in Sprint 20.

## 7. Deferred Scope

Still deferred:

- real model/provider integration;
- provider credentials and transport policy;
- structured-output provider configuration;
- semantic entailment validation;
- contradiction detection;
- relevance/semantic ranking;
- embeddings/vector retrieval;
- grounded answer history/persistence;
- model/version governance;
- cost/token accounting;
- human feedback workflows;
- automatic History-to-Knowledge ingestion;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## 8. Next Product Decision Point

Sprint 20 completes the provider-neutral Evidence-Grounded AI foundation.

The next milestone may introduce a real provider adapter only if:

- all provider calls remain behind `GroundedModelAdapter`;
- prompt/answer protocol contracts remain explicit;
- raw responses remain untrusted until strict parsing and grounding validation;
- audit trace remains available;
- secrets/network concerns stay outside domain contracts;
- provider integration does not bypass Knowledge provenance.

## 9. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
