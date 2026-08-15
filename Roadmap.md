# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 27 — Explicit History-to-Knowledge Ingestion  
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
```

## Completed Milestones

### Sprint 19 — Knowledge Domain Foundation

Immutable/versioned Knowledge records, traceable evidence references, deterministic
projection/query/comparison, read-only CLI, and real E2E.

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

Delivered:

- neutral `HistoricalSnapshotKnowledgeSource` adaptation at the CLI composition
  boundary without reversing the History dependency boundary;
- deterministic Knowledge ingestion service;
- exact re-ingestion idempotency with fail-closed identity/version conflicts;
- explicit immutable Knowledge version semantics without auto-increment;
- deterministic verified History batch ingestion;
- real History SQLite → Knowledge SQLite CLI composition;
- real archived Review Package → History import → Knowledge persistence E2E;
- exact archive checksum/evidence identity preservation;
- explicit operational scope through repeatable `--snapshot-id` or deliberate
  `--all`;
- `--dry-run` validation using the same projection semantics without creating or
  mutating the target Knowledge database;
- duplicate explicit snapshot selection rejected fail-closed.

Canonical command:

```text
python -m investment_terminal.cli.ingest_history_knowledge
```

Operational scope is mandatory:

```text
--snapshot-id <UUID>
```

or:

```text
--all
```

A non-persistent validation run uses:

```text
--dry-run
```

## Stable Authority Hierarchy

```text
Archived Review Package
→ History
→ explicit verified History-to-Knowledge ingestion
→ Knowledge
→ GroundedPromptInput
→ untrusted GroundedModelResponse
→ strict parser
→ grounding validation
→ ADMISSIBLE GroundedGenerationResult
```

History remains the downstream evidence/query boundary for archived Review
Packages. Knowledge does not import the History package. Cross-domain translation
and operational composition are owned by the CLI composition layer.

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
output-token limits, token/cost budgets, authentication, request-size
enforcement, rate limiting, and sanitized HTTP error handling.

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
- persistent usage/cost ledger;
- provider request/response persistence;
- semantic entailment/contradiction detection;
- vector retrieval/embeddings;
- grounded answer persistence/history;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## Current Decision Point

Sprint 27 implementation is complete.

Frozen Sprint 27 baseline:

```text
develop @ f95f023
```

Before selecting Sprint 28, the repository should be reviewed against current
product needs and deferred scope. Closed Sprint 27 semantics should not be
reopened without new evidence.

## Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- production composition reflects required controls;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
