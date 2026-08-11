# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 22 — Provider Governance and Usage Controls
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
→ Provider Governance and Usage Controls
```

## 2. Completed Milestones

### Sprint 19 — Knowledge Domain Foundation

Immutable/versioned Knowledge records, traceable evidence references, provenance assessment, deterministic projection/query/comparison, read-only CLI, and real E2E.

### Sprint 20 — Evidence-Grounded AI Experience Foundation

Provider-neutral grounded prompt/answer protocols, exact Knowledge citations, deterministic context selection, strict parsing, fail-closed grounding validation, provider-independent adapter boundary, audit trace, CLI, and real Knowledge SQLite E2E.

### Sprint 21 — Provider Integration and Operational AI Controls

Real OpenAI Responses API integration through provider-neutral transport and bounded retry execution, environment credential source, production composition root, live opt-in CLI, operational audit metadata, and offline-realistic provider E2E.

### Sprint 22 — Provider Governance and Usage Controls

Delivered:

- explicit provider/model allowlist policy;
- mandatory governance gate before credentials/network execution;
- live CLI governance wiring;
- provider-neutral token usage accounting;
- safe usage audit/CLI exposure;
- explicit provider/model pricing policy;
- deterministic Decimal cost accounting;
- cost audit projection;
- explicit live CLI pricing configuration;
- provider budget policy;
- real request-side `max_output_tokens`;
- pre-execution output budget enforcement;
- post-execution token budget enforcement;
- post-execution estimated-cost enforcement;
- Sprint 22 end-to-end control-path coverage.

Canonical controlled live flow:

```text
Knowledge
→ grounded prompt
→ provider/model governance
→ pre-execution budget guard
→ OpenAI request with output cap
→ provider response
→ token usage
→ strict parsing / grounding validation
→ explicit pricing
→ deterministic cost
→ post-execution token/cost guardrails
→ safe audit / CLI
```

## 3. Stable Authority Hierarchy

```text
Archived Review Package
→ History
→ Knowledge
→ GroundedPromptInput
→ untrusted GroundedModelResponse
→ strict parser
→ grounding validation
→ ADMISSIBLE GroundedGenerationResult
```

Governance, pricing, and budgets do not change evidence authority.

## 4. Provider Governance Status

Live production execution is fail-closed:

```text
explicit provider/model pair
→ ALLOWED

unknown provider/model
→ DENIED
```

There is no compatibility default that silently allows models.

## 5. Usage and Cost Status

Canonical usage:

```text
input_tokens
output_tokens
total_tokens
```

Canonical estimated cost:

```text
provider_identity
model_identity
currency
input_cost
output_cost
total_cost
```

Pricing is explicit and external to the OpenAI adapter.

No hardcoded current provider-price catalog exists.

## 6. Budget Status

Current controls:

```text
max_output_tokens
max_total_tokens
max_total_cost
currency
```

`max_output_tokens` is enforced before execution and sent as a real provider request cap.

Actual usage and estimated cost are validated after provider completion.

Budget overflow is fail-closed.

## 7. Operational Security

The live path continues to exclude from safe reports:

```text
API keys
Authorization headers
raw HTTP headers
raw HTTP bodies
provider URLs
raw model text
```

No provider control introduced by Sprint 22 mutates Knowledge, History, or portfolio state.

## 8. Deferred Scope

Still deferred:

- transport backoff/jitter;
- `Retry-After`;
- rate-limit scheduling;
- streaming;
- additional providers;
- synchronized provider pricing catalogs;
- persistent usage/cost ledger;
- provider request/response persistence;
- semantic entailment;
- contradiction detection;
- embeddings/vector retrieval;
- grounded answer persistence;
- automatic History-to-Knowledge ingestion;
- autonomous portfolio actions;
- broker execution.

## 9. Next Product Decision Point

After Sprint 22, the strongest next candidates are:

```text
A. Provider resilience / rate-limit controls
B. Application/API productization
C. Automatic Knowledge lifecycle expansion
```

The next milestone should not weaken fail-closed grounding, governance, secret isolation, or budget enforcement.

## 10. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
