# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: 3745ead
```

## Current Phase

```text
Sprint 27 CLOSED
Post-Sprint-27 review in progress
Sprint 28 not started
```

Sprint 27 — Explicit History-to-Knowledge Ingestion — is complete.

## Sprint 27 Delivered

Implemented:

- CLI-boundary adapter from verified History metadata to neutral Knowledge input;
- deterministic Knowledge ingestion service;
- exact re-ingestion idempotency;
- fail-closed identity/version conflict semantics;
- explicit immutable Knowledge versioning;
- deterministic verified History batch ingestion;
- real History SQLite → Knowledge SQLite CLI composition;
- archived Review Package → History import → Knowledge SQLite E2E;
- archive checksum/evidence identity preservation;
- mandatory operational scope through repeatable `--snapshot-id` or explicit `--all`;
- `--dry-run` projection validation without Knowledge database mutation;
- duplicate explicit snapshot IDs rejected fail-closed.

Canonical ingestion CLI:

```text
python -m investment_terminal.cli.ingest_history_knowledge
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

History remains the canonical archived-evidence boundary.

Knowledge does not import the History package.

Cross-domain History → Knowledge translation remains in the CLI composition layer.

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
- usage accounting;
- deterministic pricing/cost accounting;
- output-token limits;
- total-token budget;
- total-cost budget;
- canonical production composition of economic controls.

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
- fail-closed single-worker constraint.

## Intentional Current Limitations

Still deferred:

- automatic/scheduled History-to-Knowledge ingestion;
- distributed/multi-worker rate-limit state;
- deployment container/image and infrastructure manifests;
- TLS termination/HSTS deployment policy;
- authorization beyond API-key authentication;
- streaming grounded-AI responses;
- persistent provider usage/cost ledger;
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
Post-Sprint-27 review
→ reconcile repository inventory
→ select Sprint 28
```

Sprint 28 must not begin until current-state documentation and tracked-file inventory are reconciled.
