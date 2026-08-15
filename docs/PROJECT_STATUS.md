# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current Phase

```text
Sprint 30 CLOSED
Sprint 31 — Evidence Integrity & Delivery Hardening — IN PROGRESS
```

Current Sprint 31 completed tasks:

```text
31.1 True grounded-generation deep immutability
31.2 Strict JSON persistence boundary
31.3 Expanded architecture dependency/authority guards
```

Task 31.4 is documentation authority reconciliation.

## Stable Authority Hierarchy

```text
Archived Review Package
→ History
→ explicit verified History-to-Knowledge ingestion
→ Knowledge
→ Grounded AI
→ grounding validation
→ ADMISSIBLE generated evidence
→ persisted grounded-generation evidence
```

Parallel operational accounting:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
→ bounded queries / exact summaries
```

Neither provider accounting nor generated AI evidence gains canonical History or
Knowledge authority automatically.

## Grounded Generation Persistence

Implemented:

- deeply immutable persisted generation/trace JSON;
- strict JSON value validation;
- rejection of non-finite numbers and non-string object keys;
- detached public serialization;
- dedicated SQLite persistence;
- schema-aware readiness;
- bounded recent/time-window queries;
- read-only CLI inspection;
- authenticated read-only HTTP inspection;
- close/reopen/readback E2E.

## Production Server

Implemented:

- FastAPI production runtime;
- health/readiness;
- inbound API-key authentication;
- bounded request bodies;
- sanitized errors;
- deterministic security headers;
- process-local rate limiting;
- fail-closed single-worker constraint;
- provider governance/pricing/budgets;
- provider usage/cost persistence;
- grounded-generation persistence/readback.

Runtime routes:

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations?limit=<N>
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

## Documentation Authority

Primary canonical documents are at repository root:

```text
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
README.md
CHANGELOG.md
```

Supporting synchronized context lives under `docs/`:

```text
docs/ARCHITECTURE.md
docs/DOMAIN_MAP.md
docs/AI_CONTEXT.md
docs/PROJECT_STATUS.md
docs/README.md
```

If a supporting document conflicts with a canonical root document, the root
document is authoritative.

## Current Sprint 31 Direction

Remaining planned hardening areas include:

```text
documentation/environment reconciliation
dependency reproducibility
automated CI quality gate
closure reconciliation
```

Advanced deployment, distributed rate limiting, authorization expansion,
semantic retrieval, and generated-evidence promotion governance remain later
scope.
