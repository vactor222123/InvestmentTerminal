# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: 1cadd3e
```

## Current Phase

```text
Sprint 29 IMPLEMENTATION COMPLETE
Sprint 29 closure reconciliation in progress
Sprint 30 not started
```

Sprint 29 — Provider Operational Accounting Hardening — is implemented.

## Sprint 29 Delivered

Implemented:

- explicit mandatory provider usage/cost ledger database path;
- production initialization of configured ledger SQLite;
- ledger-aware production readiness;
- schema-version-aware readiness;
- fail-closed missing/uninitialized/corrupt ledger handling;
- isolated runtime SQLite test paths;
- bounded recent queries;
- bounded half-open time-window queries;
- bounded operational CLI commands;
- repository-owned summaries;
- exact high-precision Decimal cost aggregation;
- single-query SQLite summary aggregation;
- explicit SQLite connection lifecycle management;
- operational persistence/readiness/query/summary E2E.

Canonical operational CLI:

```text
python -m investment_terminal.cli.provider_usage_cost
```

Commands:

```text
list
recent --limit <N>
between --started-at <ISO-8601> --ended-at <ISO-8601>
show --request-id <request-id>
summary
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

Provider usage/cost ledger is a parallel operational accounting boundary. It is
not canonical History, Knowledge, or investment evidence.

## Provider Operations

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
- explicit runtime ledger database path;
- schema-aware readiness;
- bounded operational repository queries;
- exact repository summary queries;
- exact SQLite Decimal aggregation;
- read-only operational CLI;
- connection lifecycle hardening;
- production composition of economic controls and ledger recording.

## Production Server

Implemented:

- FastAPI production runtime;
- environment-backed runtime config;
- health/readiness;
- ledger schema/readiness validation;
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

## Runtime Accounting Contract

Mandatory ledger path:

```text
INVESTMENT_TERMINAL_PROVIDER_USAGE_COST_DATABASE
```

Readiness checks:

```text
knowledge_database
provider_usage_cost_database
provider_credentials
```

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
Sprint 29 closure reconciliation
→ exact tracked-file inventory reconciliation
→ post-Sprint-29 architecture/product review
→ select Sprint 30
```
