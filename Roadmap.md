# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Post-Sprint-26 Independent Repository Audit  
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
→ Post-Sprint-26 Independent Repository Audit
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
- production rate-limit end-to-end coverage.

### Post-Sprint-26 Independent Repository Audit

The repository was frozen after Sprint 26 and reviewed as one production system before Sprint 27 planning.

Confirmed findings and remediation:

```text
AUD-001 / P1
Production provider budget/pricing controls were not wired through the
canonical server composition path.
→ CLOSED at ad9dd1f

AUD-003 / P3
Canonical architecture documentation drifted behind the implemented system.
→ CLOSED at 5ec042d

AUD-002 / P3
project_files.txt no longer matched the tracked repository inventory.
→ CLOSED at 3f2f56b
```

No P0 finding remained open.

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

Server and provider controls do not change evidence authority.

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

`/docs` and `/redoc` are disabled.

Canonical production composition includes provider governance, explicit pricing, output-token limits, token/cost budgets, authentication, request-size enforcement, rate limiting, and sanitized HTTP error handling.

## 5. Canonical Inbound Request Flow

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

Authentication is evaluated before rate-limit admission.

## 6. Rate-Limit Runtime Contract

```text
INVESTMENT_TERMINAL_RATE_LIMIT_CAPACITY
INVESTMENT_TERMINAL_RATE_LIMIT_REFILL_TOKENS_PER_SECOND
```

Rate-limit state is process-local.

Canonical production CLI therefore intentionally permits only:

```text
--workers 1
```

until shared rate-limit state is explicitly designed.

## 7. Provider Economic Runtime Contract

Canonical production runtime requires explicit provider economic controls:

```text
INVESTMENT_TERMINAL_PROVIDER_MAX_OUTPUT_TOKENS
INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_TOKENS
INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_COST
INVESTMENT_TERMINAL_PROVIDER_BUDGET_CURRENCY
INVESTMENT_TERMINAL_PROVIDER_INPUT_COST_PER_MILLION_TOKENS
INVESTMENT_TERMINAL_PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS
INVESTMENT_TERMINAL_PROVIDER_PRICING_CURRENCY
```

Missing or invalid mandatory economic configuration fails closed.

## 8. Client Rate-Limit Visibility

Authenticated requests that reach admission may expose:

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

Unauthenticated `401` responses expose no limiter state.

## 9. Deferred Scope

Still deferred:

- shared/distributed rate-limit state;
- deployment container/image and infrastructure manifests;
- TLS termination/HSTS deployment policy;
- authorization beyond API-key authentication;
- retry jitter;
- proactive/concurrency-aware provider throttling;
- streaming responses;
- additional provider adapters;
- provider pricing synchronization;
- cached-token/reasoning-token pricing differentiation;
- persistent usage/cost ledger;
- provider request/response persistence;
- semantic entailment/contradiction detection;
- vector retrieval/embeddings;
- grounded answer persistence/history;
- automatic History-to-Knowledge ingestion;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## 10. Current Decision Point

Post-Sprint-26 audit remediation is complete.

Frozen post-audit baseline:

```text
develop @ 3f2f56b
```

The repository is now clear to begin Sprint 27 planning from this baseline.

Sprint 27 must be selected from current product needs and deferred scope after focused audit of the target subsystem; it must not reopen closed audit findings without new evidence.

## 11. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- production composition reflects required controls;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
