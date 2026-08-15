# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 30 — Grounded Generation Persistence & History  
**Current development branch:** `develop`

## Product Evolution

```text
Foundation
→ Current-State Analysis
→ Portfolio and Decision Intelligence
→ Unified Review Package
→ Historical Intelligence
→ Knowledge Domain
→ Evidence-Grounded AI
→ Provider Governance and Resilience
→ Production API Runtime
→ Inbound Abuse Controls
→ Explicit History-to-Knowledge Ingestion
→ Persistent Provider Usage & Cost Accounting
→ Provider Operational Accounting Hardening
→ Persistent Grounded Generation Evidence
```

## Recent Completed Milestones

### Sprint 27 — Explicit History-to-Knowledge Ingestion

Verified deterministic History → Knowledge ingestion, exact evidence/checksum
preservation, idempotent immutable versions, dry-run validation, and real E2E.

### Sprint 28 — Persistent Provider Usage & Cost Ledger

Immutable provider-neutral usage/cost accounting with dedicated SQLite
persistence and operational CLI.

### Sprint 29 — Provider Operational Accounting Hardening

Added runtime-configured ledger path, schema-aware readiness, bounded queries,
exact Decimal summary aggregation, connection lifecycle hardening, and real
operational E2E.

### Sprint 30 — Grounded Generation Persistence & History

Delivered:

- immutable `PersistedGroundedGeneration`;
- repository contract and in-memory semantics;
- deterministic projection from typed ADMISSIBLE generation + trace;
- dedicated SQLite schema/store/repository;
- application-level recording after grounding/budget checks;
- runtime-configured generation database;
- production composition;
- schema-aware readiness;
- bounded recent and half-open time-window queries;
- read-only operational CLI;
- authenticated read-only HTTP history endpoints;
- real durable Knowledge → grounded generation → persistence → reopen → HTTP
  readback E2E.

Only ADMISSIBLE grounded generations are persisted.

Persisted generations remain downstream generated evidence and do not become
History or Knowledge authority.

## Stable Authority Hierarchy

```text
Archived Review Package
→ History
→ explicit verified History-to-Knowledge ingestion
→ Knowledge
→ GroundedPromptInput
→ provider execution
→ grounding validation
→ ADMISSIBLE GroundedGenerationResult
→ persisted grounded generation evidence
```

Parallel operational accounting:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
→ bounded operational queries / exact summaries
```

## Production Routes

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations?limit=<N>
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

## Runtime Persistence Contracts

Provider accounting:

```text
INVESTMENT_TERMINAL_PROVIDER_USAGE_COST_DATABASE
```

Grounded generations:

```text
INVESTMENT_TERMINAL_GROUNDED_GENERATION_DATABASE
```

If the grounded-generation path is not explicitly configured, the runtime uses
a sibling `grounded_generations.db` next to the provider ledger.

Readiness checks:

```text
knowledge_database
provider_usage_cost_database
grounded_generation_database
provider_credentials
```

## Deferred Scope

Still deferred:

- automatic/scheduled History-to-Knowledge ingestion;
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
- semantic entailment/contradiction detection;
- vector retrieval/embeddings;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution;
- any automatic promotion of generated AI evidence into Knowledge or History.

## Current Decision Point

Sprint 30 implementation is complete.

Frozen Sprint 30 implementation baseline:

```text
develop @ 17a7fe1
```

Next:

```text
Sprint 30 documentation + inventory closure
→ focused post-Sprint-30 architecture/product audit
→ select Sprint 31
```

## Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- production composition reflects required controls;
- documentation reflects implementation;
- deferred scope is explicit;
- repository inventory is reconciled;
- repository is committed and pushed.
