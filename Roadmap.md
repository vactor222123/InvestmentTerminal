# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 26 — Inbound API Rate Limiting and Abuse Controls  
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
→ Inbound API Rate Limiting and Abuse Controls
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

Concrete FastAPI production runtime, environment-backed server configuration, production composition, liveness/readiness, inbound API-key authentication, bounded request bodies, sanitized unexpected-error handling, deterministic security headers, hardened OpenAPI, disabled production docs UIs, canonical Uvicorn CLI, and production runtime E2E.

### Sprint 26 — Inbound API Rate Limiting and Abuse Controls

Delivered:

- deterministic token-bucket rate-limit policy and decisions;
- process-local per-identity admission service;
- opaque authenticated identity derivation;
- HTTP `429` rate-limit response contract;
- `Retry-After` response metadata;
- environment-backed rate-limit capacity and refill configuration;
- monotonic Decimal production clock;
- production composition of rate-limit policy, clock, admission, and identity derivation;
- fail-closed single-worker CLI enforcement while limiter state is process-local;
- safe `RateLimit-Limit`, `RateLimit-Remaining`, and `RateLimit-Reset` client metadata;
- OpenAPI documentation of rate-limit response metadata;
- production rate-limit end-to-end coverage across runtime configuration, authentication, admission, throttling, refill, headers, and OpenAPI.

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

Server abuse controls do not change evidence authority or grounding semantics.

## 4. Production Server Status

Canonical production factory:

```text
investment_terminal.server.production:create_app
```

Canonical CLI:

```text
python -m investment_terminal.cli.server
```

Runtime routes:

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /openapi.json
```

`/docs` and `/redoc` are disabled. Health/readiness remain operational routes and are intentionally excluded from the public OpenAPI schema.

## 5. Canonical Inbound Request Flow

Authenticated grounded-AI requests follow:

```text
request
→ authentication
→ opaque rate-limit identity derivation
→ rate-limit admission
→ request-size enforcement
→ UTF-8 JSON decoding
→ framework-neutral HTTP handler
→ application/provider execution
→ sanitized server response
→ deterministic security headers
```

Authentication is evaluated before rate-limit admission. An unauthenticated request therefore fails with `401` before consuming rate-limit capacity.

## 6. Rate-Limit Runtime Contract

Runtime configuration exposes:

```text
INVESTMENT_TERMINAL_RATE_LIMIT_CAPACITY
INVESTMENT_TERMINAL_RATE_LIMIT_REFILL_TOKENS_PER_SECOND
```

The production limiter uses a monotonic clock and process-local token-bucket state.

Because limiter state is process-local, the production CLI intentionally permits only:

```text
--workers 1
```

Multi-worker execution fails closed rather than multiplying effective rate-limit capacity across independent worker processes.

## 7. Client Rate-Limit Visibility

Authenticated requests that reach rate-limit admission may expose:

```text
RateLimit-Limit
RateLimit-Remaining
RateLimit-Reset
```

A throttled request additionally returns:

```text
HTTP 429
Retry-After
```

Unauthenticated `401` responses intentionally expose no rate-limit state.

Rate-limit metadata does not expose API keys, opaque rate-limit identities, identity hashes, internal bucket keys, or provider credentials.

## 8. Public OpenAPI Contract

The public OpenAPI schema exposes only:

```text
POST /v1/grounded-ai
```

Stable operation id:

```text
grounded_ai_generate
```

Expected HTTP status surface includes:

```text
200
400
401
403
413
429
500
503
```

The schema documents safe rate-limit response metadata where admission has occurred.

## 9. Testing Status

Sprint 26 focused coverage includes:

- token-bucket policy and deterministic refill behavior;
- admission-service identity isolation;
- opaque rate-limit identity derivation;
- HTTP `429` and `Retry-After`;
- runtime environment configuration;
- monotonic production clock;
- production composition;
- single-worker CLI enforcement;
- safe rate-limit response headers;
- OpenAPI rate-limit metadata;
- production rate-limit E2E.

The final Sprint 26 closure regression result is recorded by the developer immediately before the closure commit.

## 10. Security and Authority Boundaries

Sprint 26 preserves:

- AI remains downstream of Knowledge;
- provider output remains untrusted until strict parsing and grounding validation;
- provider/model governance remains fail-closed;
- provider budget controls remain enforced at their established boundaries;
- inbound server credentials remain separate from outbound provider credentials;
- unauthenticated requests do not consume authenticated rate-limit capacity;
- rate-limit identities and credentials are excluded from API/OpenAPI surfaces;
- unexpected server failures remain sanitized;
- request bodies remain bounded before decoding;
- API/HTTP adapters do not mutate Knowledge, History, or portfolio state;
- no autonomous portfolio mutation is introduced;
- no broker execution is introduced.

## 11. Deferred Scope

Still deferred:

- shared/distributed rate-limit state for multi-worker or multi-instance deployment;
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

## 12. Next Product Decision Point

Sprint 26 completes the first inbound API abuse-control layer over the Sprint 25 production server runtime.

Before selecting Sprint 27, the repository should receive a full independent architecture and implementation audit at the final Sprint 26 baseline. Audit findings should be evidence-backed and triaged before any new feature milestone is selected.

## 13. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
