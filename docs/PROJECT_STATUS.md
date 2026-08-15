# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: ad9dd1f
```

## Current Phase

```text
Post-Sprint-26 independent audit remediation
Sprint 27 not started
```

Sprint 26 implementation, E2E coverage, and closure documentation are complete.

## Audit Status

Independent repository audit findings:

```text
AUD-001 / P1  Production provider budget/pricing composition
               CLOSED at ad9dd1f

AUD-003 / P3  Canonical architecture/documentation drift
               IN REMEDIATION

AUD-002 / P3  Repository inventory / project_files.txt drift
               PENDING
```

## AUD-001 Closure

Commit:

```text
ad9dd1f fix(server): enforce provider budgets in production
```

Canonical production runtime now requires explicit provider economic configuration and passes:

```text
requested_max_output_tokens
pricing_policy
budget_policy
```

through the production composition root into the existing application/provider control layer.

Production configuration now includes:

```text
INVESTMENT_TERMINAL_PROVIDER_MAX_OUTPUT_TOKENS
INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_TOKENS
INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_COST
INVESTMENT_TERMINAL_PROVIDER_BUDGET_CURRENCY
INVESTMENT_TERMINAL_PROVIDER_INPUT_COST_PER_MILLION_TOKENS
INVESTMENT_TERMINAL_PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS
INVESTMENT_TERMINAL_PROVIDER_PRICING_CURRENCY
```

Budget and pricing currency must match. Missing/invalid mandatory economic settings fail closed.

## Completed Foundation

### History / Historical Intelligence

Implemented:

- immutable exact-byte archive;
- append-only manifest;
- checksum/path verification;
- rebuildable SQLite projection;
- migrations and import state;
- atomic detail import;
- timeline;
- comparison;
- replay;
- outcome observations/research;
- provenance/population-quality controls.

### Knowledge / Grounded AI

Implemented:

- versioned traceable Knowledge;
- evidence references;
- provenance assessment;
- deterministic Knowledge access;
- grounded prompt contracts;
- provider-neutral generation boundary;
- strict parsing;
- grounding validation;
- grounded generation trace.

### Provider Operations

Implemented:

- OpenAI transport composition;
- provider/model governance;
- bounded retry/resilience;
- Retry-After behavior;
- usage accounting;
- deterministic pricing/cost accounting;
- output-token limits;
- total-token budget;
- total-cost budget;
- production composition of economic controls.

### Application / API

Implemented:

- provider-neutral application orchestration;
- normalized application errors;
- framework-neutral API contracts;
- deterministic HTTP mapping;
- framework-neutral HTTP handler.

### Production Server

Implemented:

- FastAPI production runtime;
- environment-backed runtime config;
- health/readiness;
- inbound API-key authentication;
- bounded request bodies;
- sanitized errors;
- deterministic security headers;
- hardened OpenAPI;
- disabled docs UIs;
- Uvicorn CLI;
- process-local inbound rate limiting;
- safe rate-limit response metadata;
- production rate-limit E2E;
- fail-closed one-worker constraint.

## Canonical Production Flow

```text
python -m investment_terminal.cli.server
→ Uvicorn factory mode
→ investment_terminal.server.production:create_app
→ runtime config
→ provider governance/pricing/budget composition
→ authentication
→ rate-limit identity derivation
→ rate-limit admission
→ request-size guardrail
→ FastAPI adapter
→ GroundedAIHTTPHandler
→ GroundedAIAPIAdapter
→ GroundedAIApplicationService
→ Knowledge / Grounded AI / provider stack
```

## Runtime Surface

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /openapi.json
```

`/health` and `/ready` are operational routes outside the public OpenAPI schema. `/docs` and `/redoc` are disabled.

## Security / Authority Status

Preserved:

- archive evidence remains immutable;
- SQLite remains rebuildable;
- Knowledge remains downstream of verified evidence;
- provider responses remain untrusted before grounding validation;
- inbound and outbound credentials are separate;
- production provider governance/budget controls are wired;
- unauthenticated requests do not consume authenticated rate-limit capacity;
- rate-limit metadata exposes no identity/secrets;
- request bodies are bounded before decoding;
- unexpected server failures remain sanitized;
- no autonomous portfolio mutation;
- no broker execution.

## Intentional Runtime Constraint

Inbound rate-limit state remains process-local.

Canonical production CLI therefore supports only:

```text
--workers 1
```

until a shared-state design is explicitly introduced.

## Current Documentation Authority

Current/canonical documents are:

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/ARCHITECTURE.md
docs/DOMAIN_MAP.md
docs/AI_CONTEXT.md
docs/README.md
```

Historical sprint plans/reviews are supporting records, not current-state authority.

## Next Steps

```text
1. Close AUD-003 canonical architecture/documentation reconciliation.
2. Reconcile AUD-002 repository inventory/project_files.txt.
3. Run final full regression.
4. Close post-Sprint-26 audit remediation.
5. Only then plan Sprint 27.
```
