# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 21 — Provider Integration and Operational AI Controls
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

Provider-neutral grounded prompt/answer protocols, exact Knowledge citations, deterministic context selection, strict parsing, fail-closed grounding validation, provider-independent adapter boundary, static reference adapter, audit trace, read-only CLI, and real Knowledge SQLite E2E.

### Sprint 21 — Provider Integration and Operational AI Controls

Delivered:

- typed provider configuration and credential-source contracts;
- environment-backed OpenAI credential resolution;
- provider-neutral transport request/response/failure contracts;
- bounded retry execution with explicit attempt semantics;
- real standard-library HTTP transport;
- OpenAI Responses API adapter with strict structured output;
- production OpenAI composition root;
- separate explicit-opt-in live CLI;
- safe provider operational metadata;
- operational audit trace and CLI exposure;
- offline-realistic provider integration E2E.

Canonical live provider flow:

```text
KnowledgeRecordEnvelope
→ deterministic context selection
→ EVIDENCE_GROUNDED_PROMPT@1
→ OpenAIGroundedModelAdapter
→ credential source
→ bounded execution
→ provider-neutral HTTP transport
→ OpenAI Responses API
→ GroundedModelResponse
→ strict JSON parser
→ EVIDENCE_GROUNDED_ANSWER@1 candidate
→ exact Knowledge grounding validation
→ ADMISSIBLE result
→ safe operational audit trace
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
    untrusted provider output + optional safe operational metadata

GroundedAIAnswer candidate
    structurally parsed but not yet trusted

GroundingValidationAssessment
    exact citation/Knowledge admissibility check

ADMISSIBLE GroundedGenerationResult
    final v1 grounded result
```

Provider integration does not change the authority hierarchy. Raw model output never outranks Knowledge evidence.

## 4. Stable AI Guardrails

Sprint 21 still does not establish:

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
GroundedModelAdapter
    provider-neutral model boundary

OpenAIGroundedModelAdapter
    concrete OpenAI Responses API adapter

GroundedProviderCredentialSource
    credential boundary

EnvironmentGroundedProviderCredentialSource
    production environment-backed credential source

GroundedProviderTransport
    provider-neutral transport boundary

UrllibGroundedProviderTransport
    real synchronous HTTP implementation

GroundedProviderExecutionService
    bounded retry orchestration
```

Production OpenAI composition remains isolated from Knowledge/History persistence.

## 6. Operational Controls

Current controls:

```text
explicit provider/model configuration
explicit environment credential mapping
timeout_seconds
max_retries
typed transport failures
bounded retry count
explicit --live CLI opt-in
request correlation
safe operational trace
```

Retry classification:

```text
TIMEOUT    → retryable
RETRYABLE  → retryable
TERMINAL   → stop
```

Current HTTP policy:

```text
408 / 425 / 429 → RETRYABLE
5xx             → RETRYABLE
other 4xx       → TERMINAL
```

No delay/backoff/jitter or `Retry-After` scheduling is implemented yet.

## 7. Audit and Persistence Status

```text
History schema target = 2
Knowledge schema target = 1
AI persistence schema = none
AI trace = derived/on demand
```

Safe provider operation metadata may include:

```text
attempt_count
retry_count
transport_status_code
transport_outcome
```

Audit/report output excludes credentials, Authorization headers, raw HTTP bodies, raw provider headers, provider URL, and raw model text.

## 8. CLI Status

Two read-only AI CLI paths now exist:

```text
grounded_ai
    static/reference provider path
    no network

grounded_ai_live
    OpenAI production composition
    explicit --live required
```

The live CLI accepts an environment-variable name for credential lookup; it does not accept the API key value directly.

## 9. Deferred Scope

Still deferred:

- streaming provider responses;
- retry delay/backoff/jitter;
- `Retry-After` handling;
- rate-limit scheduling;
- Anthropic/other provider adapters;
- model/provider allowlists;
- token/cost accounting;
- provider request/response persistence;
- semantic entailment validation;
- contradiction detection;
- relevance/semantic ranking;
- embeddings/vector retrieval;
- grounded answer history/persistence;
- prompt-template/version governance beyond current protocol contracts;
- human feedback workflows;
- automatic History-to-Knowledge ingestion;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## 10. Next Product Decision Point

Sprint 21 completes the first real-provider integration while preserving the fail-closed Evidence-Grounded AI authority boundary.

The next milestone should choose among operational governance, token/cost observability, additional provider support, or controlled streaming without weakening Knowledge provenance, parsing, grounding validation, or secret isolation.

## 11. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
