# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 24 — Application/API Productization Foundation
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
→ Application/API Productization Foundation
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

### Sprint 24 — Application/API Productization Foundation

Delivered:

- stable provider-neutral application request/result contracts;
- abstract application service boundary;
- concrete `LiveGroundedAIApplicationService`;
- migration of live CLI orchestration behind the application service;
- application composition root for Knowledge/provider/application construction;
- migration of CLI construction behind the application composition root;
- stable application error contract with normalized categories and codes;
- framework-neutral API request/response DTOs;
- framework-neutral API adapter over the application service;
- deterministic HTTP status mapping;
- framework-neutral HTTP handler for decoded request payloads;
- fail-closed invalid payload handling;
- API composition root returning a fully assembled HTTP handler.

Canonical productization flow:

```text
external transport/server adapter
→ API composition
→ framework-neutral HTTP handler
→ API request/response contract
→ application service
→ Knowledge / grounded generation / provider stack
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

Application/API productization does not change evidence authority or grounding semantics.

## 4. Application Boundary Status

Canonical application request:

```text
request_id
user_query
subject_keys
max_items
```

Canonical application result:

```text
generation
trace
```

Application callers no longer need CLI-specific argument parsing, SQLite construction, provider composition, or credential handling.

## 5. Application Error Contract

Stable categories:

```text
POLICY_DENIED
INVALID_REQUEST
EXECUTION_FAILED
INTERNAL_ERROR
```

Stable codes:

```text
APPLICATION_POLICY_DENIED
APPLICATION_INVALID_REQUEST
APPLICATION_EXECUTION_FAILED
APPLICATION_INTERNAL_ERROR
```

Known lower-layer exceptions are normalized at the application boundary while preserving the original exception as internal cause.

Unknown internal failures are sanitized before leaving the application boundary.

## 6. API Contract Status

Canonical API request:

```text
request_id
query
subjects
max_items
```

Unknown request fields fail closed.

Canonical API response:

```text
status
request_id
data | error
```

Application errors are represented as stable API errors instead of raw provider, persistence, or Python exceptions.

## 7. HTTP Semantics

Deterministic mapping:

```text
SUCCESS          → 200
INVALID_REQUEST  → 400
POLICY_DENIED    → 403
EXECUTION_FAILED → 503
INTERNAL_ERROR   → 500
unknown category → 500
```

Malformed decoded payloads are converted to stable `400` responses.

No concrete web framework is required for the current handler.

## 8. Composition Status

Application composition:

```text
build_live_grounded_ai_application()
```

owns:

```text
KnowledgeSQLiteStore
→ SQLiteKnowledgeRecordRepository
→ KnowledgeQueryService

OpenAI provider composition
→ GroundedGenerationService

both
→ LiveGroundedAIApplicationService
```

API composition:

```text
build_live_grounded_ai_http_handler()
```

owns:

```text
application composition
→ GroundedAIHTTPHandler
```

Future server adapters should depend on the API composition root rather than on Knowledge/provider construction details.

## 9. CLI Status

The live CLI is now a thin adapter:

```text
parse arguments
→ build policies
→ application composition
→ application request
→ application result
→ JSON / human rendering
```

Legacy `_run_live()` remains as a backward-compatible programmatic seam for existing tests/callers.

## 10. Testing Status

Sprint 24 closure regression:

```text
1865 passed, 3 skipped in 9.04s
```

Sprint 24 focused coverage includes:

- application request/result validation;
- concrete application orchestration;
- application dependency/fail-fast semantics;
- CLI-to-application migration;
- application composition;
- CLI-to-composition migration;
- application error normalization;
- API request/response contracts;
- HTTP status mapping;
- malformed payload handling;
- API composition wiring.

## 11. Security and Authority Boundaries

Sprint 24 preserves:

- AI remains downstream of Knowledge;
- provider output remains untrusted until strict parsing and grounding validation;
- provider/model governance remains fail-closed;
- budget enforcement remains before/after provider execution as designed;
- API keys remain outside application/API response surfaces;
- raw provider headers, bodies, URLs, and transport messages remain excluded;
- API/HTTP adapters do not mutate Knowledge, History, or portfolio state;
- no autonomous portfolio mutation is introduced;
- no broker execution is introduced.

## 12. Deferred Scope

Still deferred:

- concrete web-framework runtime (FastAPI/Flask/etc.);
- route registration/server startup;
- authentication and authorization middleware;
- API schema publication/OpenAPI;
- health/readiness endpoints;
- deployment/runtime packaging;
- rate limiting at the inbound API layer;
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

## 13. Next Product Decision Point

After Sprint 24, the system has a stable application boundary and a framework-neutral API/HTTP layer.

The strongest next candidates are:

```text
A. Real web server runtime and route adapter
B. Authentication / authorization foundation
C. Provider concurrency / rate-limit scheduler
```

The next milestone must preserve fail-closed grounding, governance, secret isolation, budget enforcement, and safe error/audit boundaries.

## 14. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
