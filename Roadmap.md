# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 25 — Production Server Runtime and HTTP Hardening
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
→ Production Server Runtime and HTTP Hardening
```

## 2. Completed Milestones

### Sprint 19 — Knowledge Domain Foundation

Immutable/versioned Knowledge records, traceable evidence references, provenance assessment, deterministic projection/query/comparison, read-only CLI, and real E2E.

### Sprint 20 — Evidence-Grounded AI Experience Foundation

Provider-neutral grounded prompt/answer protocols, exact Knowledge citations, deterministic context selection, strict parsing, fail-closed grounding validation, provider-independent adapter boundary, audit trace, CLI, and real Knowledge SQLite E2E.

### Sprint 21 — Provider Integration and Operational AI Controls

Real OpenAI Responses API integration through provider-neutral transport and bounded retry execution, environment credential source, production composition root, live opt-in CLI, operational audit metadata, and offline-realistic provider E2E.

### Sprint 22 — Provider Governance and Usage Controls

Provider/model allowlisting, usage accounting, deterministic pricing/cost accounting, provider budgets, request-side output limits, and pre/post-execution enforcement.

### Sprint 23 — Provider Resilience and Rate-Limit Controls

Deterministic bounded retry delay, Retry-After support, injectable sleeper/clock boundaries, conservative delay precedence, retry-delay audit metadata, and resilience E2E.

### Sprint 24 — Application/API Productization Foundation

Stable provider-neutral application contracts, application composition, normalized application errors, framework-neutral API contracts, deterministic HTTP mapping, framework-neutral HTTP handler, and API composition root.

### Sprint 25 — Production Server Runtime and HTTP Hardening

Delivered:

- concrete FastAPI production runtime over the framework-neutral API boundary;
- environment-backed server runtime configuration;
- production server composition root;
- liveness and readiness routes;
- inbound API-key authentication;
- bounded inbound request-body size enforcement;
- sanitized server-level unexpected-error boundary;
- deterministic security response headers;
- hardened public OpenAPI contract;
- operational health/readiness routes excluded from public OpenAPI;
- Swagger and ReDoc production UIs disabled;
- canonical Uvicorn production CLI entrypoint;
- production runtime end-to-end coverage.

Canonical production flow:

```text
process / Uvicorn
→ production create_app()
→ runtime configuration
→ authentication
→ request-size guardrail
→ FastAPI transport adapter
→ framework-neutral HTTP handler
→ API contract
→ application service
→ Knowledge / grounded generation / provider stack
→ sanitized server response
→ security response headers
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

Server productization does not change evidence authority or grounding semantics.

## 4. Production Server Status

Canonical production factory:

```text
investment_terminal.server.production:create_app
```

Canonical CLI:

```text
python -m investment_terminal.cli.server
```

The CLI owns process-level Uvicorn configuration only. Environment parsing, server security policy, API composition, application composition, Knowledge access, and provider construction remain behind their existing boundaries.

Runtime routes:

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /openapi.json
```

`/docs` and `/redoc` are disabled.

Health/readiness remain operational routes and are intentionally excluded from the public OpenAPI schema.

## 5. Server Security Boundary

Inbound grounded-AI requests follow:

```text
authentication
→ request-size enforcement
→ UTF-8 JSON decoding
→ framework-neutral HTTP handler
→ application/provider execution
→ sanitized unexpected-error boundary
→ deterministic security headers
```

Known transport/application failures preserve their stable semantics.

Unexpected server failures return a generic internal-error response rather than raw Python, persistence, provider, path, credential, header, or request-body details.

## 6. Authentication

`POST /v1/grounded-ai` requires the configured inbound `X-API-Key`.

Inbound server authentication is distinct from outbound provider credentials.

Authentication is evaluated before request-body processing so unauthenticated requests fail closed before payload decoding or application execution.

## 7. Request Limits

The production runtime enforces a bounded request-body size before JSON decoding.

Oversized authenticated requests return HTTP `413`.

The configured request-body limit belongs to the server runtime boundary and does not alter application-domain contracts.

## 8. Public OpenAPI Contract

The public OpenAPI schema exposes only:

```text
POST /v1/grounded-ai
```

Stable operation id:

```text
grounded_ai_generate
```

Canonical request fields:

```text
request_id
query
subjects
max_items
```

Unknown fields fail closed.

Expected HTTP status surface includes:

```text
200
400
401
403
413
500
503
```

Internal implementation classes, runtime secrets, and provider credential names are not part of the public schema.

## 9. HTTP Semantics

Core deterministic application mapping remains:

```text
SUCCESS          → 200
INVALID_REQUEST  → 400
POLICY_DENIED    → 403
EXECUTION_FAILED → 503
INTERNAL_ERROR   → 500
unknown category → 500
```

Server-specific transport failures additionally include:

```text
UNAUTHENTICATED     → 401
REQUEST_TOO_LARGE   → 413
INVALID_JSON        → 400
unexpected failure  → sanitized 500
```

## 10. Testing Status

Sprint 25 closure regression:

```text
1928 passed, 3 skipped, 1 warning in 16.74s
```

Sprint 25 focused coverage includes:

- runtime environment configuration;
- production server composition;
- health/readiness behavior;
- inbound authentication;
- request-size enforcement;
- sanitized server errors;
- security response headers;
- hardened OpenAPI surface;
- production CLI process delegation;
- production runtime E2E across environment, composition, HTTP, auth, limits, application seam, readiness, security headers, and schema exposure.

## 11. Security and Authority Boundaries

Sprint 25 preserves:

- AI remains downstream of Knowledge;
- provider output remains untrusted until strict parsing and grounding validation;
- provider/model governance remains fail-closed;
- budget controls remain in their established application/provider boundaries;
- inbound server credentials remain separate from outbound provider credentials;
- credentials are not returned through API/OpenAPI response surfaces;
- raw provider headers, bodies, URLs, and transport messages remain excluded;
- unexpected server failures are sanitized;
- request bodies are bounded before decoding;
- API/HTTP adapters do not mutate Knowledge, History, or portfolio state;
- no autonomous portfolio mutation is introduced;
- no broker execution is introduced.

## 12. Deferred Scope

Still deferred:

- inbound API rate limiting / throttling;
- deployment container/image and infrastructure manifests;
- TLS termination policy and HSTS deployment policy;
- authorization beyond the current API-key authentication boundary;
- retry jitter;
- proactive provider rate-limit scheduling;
- concurrency-aware provider throttling;
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

Sprint 25 completes the first production HTTP runtime and server-hardening milestone over the Sprint 24 application/API foundation.

Strong next candidates are:

```text
A. Inbound API rate limiting and abuse controls
B. Deployment/container/runtime operations foundation
C. Provider concurrency and proactive rate-limit scheduling
```

The next milestone must preserve fail-closed grounding, governance, secret isolation, budget enforcement, stable API contracts, and sanitized server boundaries.

## 14. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
