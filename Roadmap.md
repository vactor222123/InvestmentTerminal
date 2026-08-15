# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 28 — Persistent Provider Usage & Cost Ledger  
**Current development branch:** `develop`

## Current Product Evolution

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
```

## Completed Milestones

### Sprint 19 — Knowledge Domain Foundation

Immutable/versioned Knowledge records, traceable evidence references,
deterministic projection/query/comparison, read-only CLI, and real E2E.

### Sprint 20 — Evidence-Grounded AI Experience Foundation

Provider-neutral grounded prompt/answer protocols, exact Knowledge citations,
strict parsing, grounding validation, audit trace, CLI, and real Knowledge E2E.

### Sprints 21–23 — Provider Integration, Governance, and Resilience

Production provider composition, allowlisting, usage/cost controls, budgets,
bounded retry execution, Retry-After handling, deterministic delay policy, and
provider operational audit metadata.

### Sprints 24–26 — Production API and Inbound Controls

Framework-neutral application/API contracts, FastAPI production runtime,
authentication, request-size enforcement, sanitized errors, security headers,
hardened OpenAPI, canonical Uvicorn CLI, and deterministic inbound rate limiting.

### Sprint 27 — Explicit History-to-Knowledge Ingestion

Delivered explicit verified History → Knowledge ingestion with deterministic
batching, exact evidence/checksum preservation, real SQLite composition, real
archive-to-Knowledge E2E, mandatory selection scope, idempotency, immutable
version semantics, and dry-run operational validation.

Canonical command:

```text
python -m investment_terminal.cli.ingest_history_knowledge
```

### Sprint 28 — Persistent Provider Usage & Cost Ledger

Delivered:

- immutable provider-neutral usage/cost ledger record;
- repository contract and in-memory reference implementation;
- dedicated SQLite schema/store;
- SQLite repository with exact Decimal text round-trip;
- recording service over already-observed usage and deterministic cost;
- production application composition for durable recording;
- read-only operational CLI;
- exact request identity and immutable duplicate rejection;
- deterministic `(recorded_at, request_id)` ordering;
- real SQLite close/reopen persistence E2E.

Canonical operational CLI:

```text
python -m investment_terminal.cli.provider_usage_cost
```

Supported read-only commands:

```text
list
show --request-id <request-id>
summary
```

The ledger records successful priced provider usage after application execution.
It does not replace Grounded AI trace data and does not become canonical
historical investment evidence.

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
```

Provider operational accounting remains a parallel operational evidence stream:

```text
successful priced provider usage
→ immutable usage/cost ledger
```

It must not be promoted into History or Knowledge authority.

## Production Server Status

Canonical production factory:

```text
investment_terminal.server.production:create_app
```

Canonical server CLI:

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

Production composition includes provider governance, explicit pricing,
output-token limits, token/cost budgets, persistent successful usage/cost
recording, authentication, request-size enforcement, rate limiting, and
sanitized HTTP error handling.

## Rate-Limit Runtime Contract

```text
INVESTMENT_TERMINAL_RATE_LIMIT_CAPACITY
INVESTMENT_TERMINAL_RATE_LIMIT_REFILL_TOKENS_PER_SECOND
```

Rate-limit state remains process-local. The canonical production server CLI
therefore permits only:

```text
--workers 1
```

until shared rate-limit state is explicitly designed.

## Provider Economic Runtime Contract

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
- provider request/response persistence;
- grounded answer persistence/history;
- semantic entailment/contradiction detection;
- vector retrieval/embeddings;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## Current Decision Point

Sprint 28 implementation is complete.

Frozen Sprint 28 implementation baseline:

```text
develop @ cffc060
```

Before selecting Sprint 29, reconcile canonical documentation and tracked-file
inventory, then run a focused architecture/product-boundary review.

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
