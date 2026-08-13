# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: 5d3d602
```

## Current phase

```text
Sprint 25 — Production Server Runtime and HTTP Hardening
implementation complete
full regression green
ready for closure documentation commit
```

## Completed foundation

### Sprint 12–23

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, provenance/population quality, archive continuity, Knowledge Domain, Evidence-Grounded AI, real OpenAI provider integration, governance, usage, pricing, budget controls, and provider resilience are complete.

### Sprint 24 — Application/API Productization Foundation

Stable application contracts, concrete application orchestration, application composition, normalized application errors, framework-neutral API contracts, deterministic HTTP mapping, framework-neutral HTTP handler, and API composition are complete.

### Sprint 25 — Production Server Runtime and HTTP Hardening

Delivered:

```text
FastAPI production runtime
environment-backed runtime configuration
production server composition
GET /health
GET /ready
inbound X-API-Key authentication
request-body size enforcement
sanitized unexpected-error boundary
security response headers
hardened public OpenAPI contract
disabled Swagger/ReDoc production UIs
canonical Uvicorn CLI entrypoint
production runtime E2E
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
server auth / request limits
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

Operational `/health` and `/ready` routes remain outside the public OpenAPI schema.

Swagger `/docs` and ReDoc `/redoc` are disabled.

## Authentication Boundary

`POST /v1/grounded-ai` requires the configured inbound `X-API-Key`.

Authentication is evaluated before request-body processing.

The inbound server key is separate from the outbound OpenAI/provider credential.

## Request Boundary

Authenticated request bodies are bounded before UTF-8 JSON decoding.

Expected server transport behavior:

```text
missing/invalid API key → 401
invalid JSON            → 400
oversized body          → 413
application policy      → 403
application unavailable → 503
unexpected server error → sanitized 500
```

## Error Boundary

Unexpected exceptions are converted to a stable generic internal-error response.

The response does not intentionally expose:

```text
raw exception text
tracebacks
filesystem paths
credentials
provider secrets
raw provider transport details
request bodies
```

Known HTTP/application failures retain their established mappings.

## Security Headers

Production responses receive deterministic hardening headers including:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Cache-Control: no-store
Pragma: no-cache
```

HSTS remains a deployment/TLS concern and is not assumed by the application runtime.

## Public OpenAPI Contract

Public schema surface:

```text
POST /v1/grounded-ai
```

Stable operation id:

```text
grounded_ai_generate
```

Request:

```text
request_id
query
subjects
max_items
```

The schema rejects additional request properties.

Documented response status surface includes:

```text
200
400
401
403
413
500
503
```

Internal implementation types and secret values are not part of the public contract.

## Production CLI

Canonical launch command:

```text
python -m investment_terminal.cli.server
```

The CLI delegates to:

```text
investment_terminal.server.production:create_app
```

through Uvicorn factory mode.

The CLI owns process options only and does not duplicate Knowledge, provider, application, API, auth, readiness, or runtime composition.

## Testing Status

Full regression at Sprint 25 closure:

```text
1928 passed, 3 skipped, 1 warning in 16.74s
```

Focused Sprint 25 coverage includes:

```text
runtime configuration
production composition
health/readiness
authentication
request limits
server error sanitization
security headers
OpenAPI hardening
server CLI
production runtime E2E
```

The production E2E covers the real server composition and HTTP stack while replacing only the outbound application/provider seam with deterministic network-free behavior.

## Security and Authority Boundaries

Sprint 25 preserves:

- AI remains downstream of Knowledge;
- no server/API adapter bypasses grounding validation;
- provider/model governance remains fail-closed;
- provider budget controls remain enforced at their established boundaries;
- inbound API credentials remain separate from outbound provider credentials;
- credentials are excluded from public API/OpenAPI surfaces;
- raw provider transport data remains outside API responses;
- request size is bounded before decoding;
- unexpected server failures are sanitized;
- no HTTP path mutates Knowledge or History;
- no AI persistence schema is introduced;
- no autonomous portfolio mutation is introduced;
- no broker execution is introduced.

## Deferred Capabilities

Still deferred:

- inbound API rate limiting and abuse throttling;
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

Sprint 25 completes the production server/runtime foundation over the stable Sprint 24 application/API boundary.

The next milestone should be selected explicitly rather than extending Sprint 25. Leading candidates are inbound API rate limiting/abuse controls, deployment/runtime operations, or provider concurrency/rate-limit scheduling.
