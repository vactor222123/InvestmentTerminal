# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: cffc060
```

## Current Phase

```text
Sprint 28 IMPLEMENTATION COMPLETE
Sprint 28 closure reconciliation in progress
Sprint 29 not started
```

Sprint 28 — Persistent Provider Usage & Cost Ledger — is implemented.

## Sprint 28 Delivered

Implemented:

- immutable provider usage/cost ledger record;
- provider-neutral repository contract;
- in-memory reference repository;
- dedicated SQLite schema/store;
- SQLite repository;
- exact Decimal cost persistence without float conversion;
- recording service over observed usage + deterministic pricing result;
- production application composition;
- immutable duplicate request rejection;
- deterministic chronological/request-id ordering;
- read-only operational CLI;
- exact summary aggregation;
- real SQLite persistence/reopen E2E.

Canonical operational CLI:

```text
python -m investment_terminal.cli.provider_usage_cost
```

## Stable Authority Hierarchy

```text
Archived Review Package
→ History
→ explicit verified History-to-Knowledge ingestion
→ Knowledge
→ Grounded AI
→ Application / API
→ Production Server
```

Provider usage/cost ledger is an operational accounting boundary. It is not
canonical History, Knowledge, or investment evidence.

## Current System Foundation

### History / Historical Intelligence

Implemented:

- immutable exact-byte archive;
- append-only manifest;
- checksum/path verification;
- rebuildable SQLite projection;
- migrations and explicit import state;
- atomic detail import;
- timeline;
- comparison and replay;
- outcome observations/research;
- provenance/population-quality controls.

### Knowledge / Grounded AI

Implemented:

- versioned traceable Knowledge;
- evidence references;
- provenance assessment;
- deterministic projection/query/comparison;
- explicit verified History ingestion;
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
- deterministic usage accounting;
- deterministic pricing/cost accounting;
- output-token limits;
- total-token budget;
- total-cost budget;
- persistent immutable successful usage/cost ledger;
- read-only usage/cost operational CLI;
- production composition of economic controls and ledger recording.

### Application / API

Implemented:

- provider-neutral application orchestration;
- normalized application errors;
- framework-neutral API contracts;
- deterministic HTTP mapping;
- framework-neutral HTTP handler;
- successful priced usage/cost recording decorator.

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
- fail-closed single-worker constraint;
- persistent provider usage/cost accounting.

## Intentional Current Limitations

Still deferred:

- automatic/scheduled History-to-Knowledge ingestion;
- distributed/multi-worker rate-limit state;
- deployment container/image and infrastructure manifests;
- TLS termination/HSTS deployment policy;
- authorization beyond API-key authentication;
- streaming grounded-AI responses;
- provider request/response persistence;
- grounded answer persistence/history;
- vector retrieval/embeddings;
- semantic entailment/contradiction detection;
- autonomous portfolio mutation;
- broker execution.

## Current Documentation Authority

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/ARCHITECTURE.md
docs/DOMAIN_MAP.md
docs/AI_CONTEXT.md
docs/README.md
NEXT_STEPS.md
```

## Next Step

```text
Sprint 28 closure reconciliation
→ exact tracked-file inventory reconciliation
→ post-Sprint-28 architecture/product review
→ select Sprint 29
```
