# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 23 — Provider Resilience and Rate-Limit Controls
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
→ Provider Resilience and Rate-Limit Controls
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

### Sprint 23 — Provider Resilience and Rate-Limit Controls

Delivered:

- deterministic retry-delay policy;
- explicit initial delay, multiplier, and maximum local delay;
- bounded exponential local backoff;
- injectable sleeper boundary;
- production time-based sleeper composition;
- live CLI retry-delay configuration;
- provider-neutral `retry_after_seconds` transport metadata;
- `Retry-After` delta-seconds parsing at the HTTP boundary;
- conservative `max(local backoff, provider Retry-After)` precedence;
- HTTP-date `Retry-After` parsing;
- injectable UTC clock for deterministic time-based tests;
- applied retry-delay operational metadata;
- safe retry-delay audit projection;
- JSON and human CLI retry-delay visibility;
- deterministic resilience E2E covering rate-limit retry, delay precedence, successful recovery, audit, and CLI output.

Canonical resilient provider flow:

```text
provider request
→ retryable transport failure
→ Retry-After metadata
→ deterministic bounded local backoff
→ effective delay = max(local delay, provider delay)
→ sleeper
→ bounded retry
→ provider success
→ strict parsing / grounding validation
→ safe operational audit
→ JSON / human CLI
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

Provider resilience changes execution timing only. It does not change evidence authority.

## 4. Provider Governance Status

Live production execution remains fail-closed:

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

Pricing remains explicit and external to the OpenAI adapter.

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

Budget overflow remains fail-closed.

## 7. Resilience Status

Current retry controls:

```text
max_retries
retry_initial_delay_seconds
retry_delay_multiplier
retry_maximum_delay_seconds
Retry-After delta-seconds
Retry-After HTTP-date
injectable sleeper
injectable UTC clock
```

Local retry delay is bounded by the configured maximum.

Provider-requested `Retry-After` is not truncated by the local maximum.

Effective retry delay is:

```text
max(local policy delay, provider Retry-After)
```

Terminal failures are never delayed or retried.

No delay is applied after the final exhausted attempt.

## 8. Operational Security

The live path continues to exclude from safe reports:

```text
API keys
Authorization headers
raw HTTP headers
raw HTTP bodies
provider URLs
raw provider failure messages
raw model text
```

Safe resilience audit data may include:

```text
attempt_count
retry_count
transport_status_code
transport_outcome
retry_delay_seconds
```

No provider resilience control mutates Knowledge, History, or portfolio state.

## 9. Testing Status

Sprint 23 closure regression:

```text
1819 passed, 3 skipped
```

The resilience E2E verifies:

```text
real Knowledge SQLite
→ retryable 429-like provider failure
→ provider retry delay
→ local/provider delay precedence
→ deterministic fake sleeper
→ successful retry
→ grounded admissible answer
→ safe operational trace
→ human CLI retry-delay output
```

No real API key, real sleep, or network access is required for the resilience E2E.

## 10. Deferred Scope

Still deferred:

- retry jitter;
- proactive provider rate-limit scheduling;
- concurrency-aware throttling;
- streaming responses;
- additional provider adapters;
- provider pricing catalog synchronization;
- cached-token/reasoning-token pricing differentiation;
- persistent usage/cost ledger;
- provider request/response persistence;
- semantic entailment validation;
- contradiction detection;
- vector retrieval/embeddings;
- grounded answer persistence/history;
- automatic History-to-Knowledge ingestion;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## 11. Next Product Decision Point

After Sprint 23, the provider execution path has governance, budgets, usage/cost accounting, deterministic retries, and server-directed retry timing.

The strongest next candidates are:

```text
A. Application/API productization
B. Provider concurrency/rate-limit scheduler
C. Automatic Knowledge lifecycle expansion
```

The next milestone must preserve fail-closed grounding, governance, secret isolation, budget enforcement, and safe audit boundaries.

## 12. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
