# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: e3f3a5b
```

The baseline above is the implementation-complete Sprint 26 baseline immediately before the closure documentation commit.

## Current Phase

```text
Sprint 26 — Inbound API Rate Limiting and Abuse Controls
implementation complete
production E2E complete
closure documentation in progress
```

## Completed Foundation

### Sprint 12–23

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, provenance/population quality, archive continuity, Knowledge Domain, Evidence-Grounded AI, real OpenAI provider integration, governance, usage, pricing, budget controls, and provider resilience are complete.

### Sprint 24 — Application/API Productization Foundation

Stable application contracts, concrete application orchestration, application composition, normalized application errors, framework-neutral API contracts, deterministic HTTP mapping, framework-neutral HTTP handler, and API composition are complete.

### Sprint 25 — Production Server Runtime and HTTP Hardening

FastAPI production runtime, environment-backed runtime configuration, production server composition, health/readiness, inbound API-key authentication, request-size enforcement, sanitized unexpected-error boundary, security response headers, hardened OpenAPI, disabled production docs UIs, canonical Uvicorn CLI, and production runtime E2E are complete.

### Sprint 26 — Inbound API Rate Limiting and Abuse Controls

Delivered:

```text
token-bucket rate-limit policy
per-authenticated-identity admission
opaque identity derivation
HTTP 429 throttling contract
Retry-After
environment-backed capacity/refill configuration
monotonic Decimal production clock
production limiter composition
single-worker fail-closed CLI enforcement
RateLimit-Limit
RateLimit-Remaining
RateLimit-Reset
OpenAPI rate-limit metadata
production rate-limit E2E
```

## Canonical Production Flow

```text
python -m investment_terminal.cli.server
        ↓
Uvicorn factory mode
        ↓
investment_terminal.server.production:create_app
        ↓
runtime configuration
        ↓
authentication
        ↓
rate-limit identity derivation
        ↓
rate-limit admission
        ↓
request-size guardrail
        ↓
FastAPI transport adapter
        ↓
GroundedAIHTTPHandler
        ↓
GroundedAIAPIAdapter
        ↓
GroundedAIApplicationService
        ↓
Knowledge / GroundedGeneration / provider stack
```

## Runtime Surface

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /openapi.json
```

Operational `/health` and `/ready` routes remain outside the public OpenAPI schema. Swagger `/docs` and ReDoc `/redoc` remain disabled.

## Authentication and Rate-Limit Boundary

`POST /v1/grounded-ai` requires the configured inbound `X-API-Key`.

Canonical ordering:

```text
authentication
→ rate-limit identity derivation
→ rate-limit admission
→ body processing
```

Therefore:

```text
missing/invalid API key
→ 401
→ no authenticated rate-limit token consumed
→ no RateLimit-* state exposed
```

Authenticated admitted requests receive safe aggregate limiter metadata. Authenticated throttled requests receive `429`, `Retry-After`, and safe limiter metadata.

## Rate-Limit Runtime Configuration

```text
INVESTMENT_TERMINAL_RATE_LIMIT_CAPACITY
INVESTMENT_TERMINAL_RATE_LIMIT_REFILL_TOKENS_PER_SECOND
```

Rate-limit state is process-local.

Until state ownership becomes shared across workers/processes, production execution intentionally supports only:

```text
--workers 1
```

The CLI fails closed for larger worker counts so independent process-local buckets cannot multiply effective capacity.

## Client Rate-Limit Contract

Safe response metadata:

```text
RateLimit-Limit
RateLimit-Remaining
RateLimit-Reset
```

Throttled response:

```text
HTTP 429
Retry-After
```

The public surface does not expose:

```text
API keys
opaque rate-limit identities
identity hashes
internal bucket keys
provider credentials
```

## Request Boundary

Authenticated and admitted request bodies remain bounded before UTF-8 JSON decoding.

Expected server transport behavior:

```text
missing/invalid API key → 401
rate limit exceeded     → 429
invalid JSON            → 400
oversized body          → 413
application policy      → 403
application unavailable → 503
unexpected server error → sanitized 500
```

## Public OpenAPI Contract

Public schema surface:

```text
POST /v1/grounded-ai
```

Stable operation id:

```text
grounded_ai_generate
```

Documented response status surface includes:

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

OpenAPI documents safe `RateLimit-*` metadata on responses that may follow admission and `Retry-After` on `429`.

## Testing Status

Sprint 26 focused coverage includes:

```text
rate-limit policy
admission service
identity derivation
HTTP throttling
runtime configuration
monotonic clock
production composition
CLI worker enforcement
response headers
OpenAPI metadata
production rate-limit E2E
```

The production E2E verifies the real production composition path with deterministic seams and covers:

```text
runtime env
→ production create_app()
→ authentication
→ admission
→ 200
→ 429
→ deterministic refill
→ 200
```

It also verifies that unauthenticated requests do not consume authenticated limiter capacity.

The final full-suite count is intentionally not hard-coded here until the developer runs the closure regression on the exact documentation package working tree.

## Security and Authority Boundaries

Sprint 26 preserves:

- AI remains downstream of Knowledge;
- no server/API adapter bypasses grounding validation;
- provider/model governance remains fail-closed;
- provider budget controls remain enforced at their established boundaries;
- inbound API credentials remain separate from outbound provider credentials;
- rate-limit identity is opaque and remains internal;
- unauthenticated requests do not expose rate-limit state;
- raw provider transport data remains outside API responses;
- request size remains bounded before decoding;
- unexpected server failures remain sanitized;
- no HTTP path mutates Knowledge or History;
- no AI persistence schema is introduced;
- no autonomous portfolio mutation is introduced;
- no broker execution is introduced.

## Deferred Capabilities

Still deferred:

- shared/distributed rate-limit state for multi-worker or multi-instance deployment;
- deployment container/image and infrastructure manifests;
- TLS termination/HSTS deployment policy;
- authorization beyond API-key authentication;
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

## Next Decision

Sprint 26 implementation is complete.

After this closure documentation package is green and committed, freeze that commit as the Sprint 26 final baseline and perform a full independent repository audit before selecting or implementing Sprint 27.

The audit should inspect the repository as one production system and should report evidence-backed findings without modifying code on the first pass.
