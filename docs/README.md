# Investment Terminal

> A private, local-first investment intelligence platform built around deterministic analysis, preserved evidence, traceable Knowledge, evidence-grounded AI assistance, and explicit operational accounting.

**Status:** Active development  
**Latest completed implementation milestone:** Sprint 28 — Persistent Provider Usage & Cost Ledger  
**Current phase:** Sprint 28 closure reconciliation  
**Primary language:** Python

## Overview

Investment Terminal is a modular monolith for long-term investment analysis and
disciplined review workflows.

Established capability layers include:

```text
Current-State Analysis
→ Portfolio / Decision Intelligence
→ Review Package
→ Immutable History
→ Historical Intelligence / Outcome Research
→ explicit verified History-to-Knowledge ingestion
→ Knowledge
→ Grounded AI
→ Application / API
→ Production Server
```

A parallel operational accounting stream now exists:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
```

That ledger is operational evidence only. It does not become canonical History or
Knowledge.

## Sprint 28

Sprint 28 adds durable provider usage/cost accounting while preserving existing
provider, grounding, application, History, and Knowledge boundaries.

Implemented:

- immutable ledger record;
- repository contract;
- SQLite store and repository;
- exact Decimal persistence;
- recording service;
- production composition;
- read-only operational CLI;
- deterministic summaries;
- real persistence E2E.

Operational CLI:

```text
python -m investment_terminal.cli.provider_usage_cost
```

Commands:

```text
list
show --request-id <request-id>
summary
```

## Historical Evidence

Canonical historical authority remains:

```text
Review Package
→ immutable archived JSON
→ append-only manifest
→ verified/rebuildable SQLite History
```

Archived JSON remains canonical historical evidence. Provider operational
accounting does not alter this hierarchy.

## Grounded AI

Grounded AI remains downstream of Knowledge:

```text
Knowledge
→ GroundedPromptInput
→ provider
→ untrusted response
→ strict parser
→ grounding validation
→ admissible grounded generation
```

Successful priced usage can then be persisted to the provider usage/cost ledger.

## Production Surface

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

Production currently supports one worker because inbound rate-limit state is
process-local.

## Provider Controls

Canonical production composition includes:

- provider/model allowlisting;
- bounded retry/resilience;
- explicit output-token limit;
- total-token budget;
- total-cost budget;
- explicit provider pricing policy;
- deterministic usage/cost accounting;
- persistent successful usage/cost ledger;
- environment-backed provider credentials.

## Main Engineering Principles

Investment Terminal prioritizes:

1. correctness;
2. determinism;
3. historical integrity;
4. explainability;
5. explicit ownership;
6. fail-closed security/governance;
7. maintainability;
8. focused changes;
9. production composition tests;
10. human decision ownership.

## Canonical Documentation

```text
Roadmap.md
NEXT_STEPS.md
docs/PROJECT_STATUS.md
docs/ARCHITECTURE.md
docs/DOMAIN_MAP.md
docs/AI_CONTEXT.md
docs/README.md
```

## Testing

Full suite:

```powershell
python -m pytest -q
```

## Current Deferred Scope

Not currently claimed:

- automatic/scheduled History-to-Knowledge ingestion;
- distributed/multi-worker rate-limit state;
- deployment/infrastructure hardening;
- autonomous trading;
- broker execution;
- streaming grounded-AI responses;
- provider pricing synchronization;
- provider request/response persistence;
- grounded answer persistence/history;
- vector retrieval/embeddings.

## Current Phase

```text
Sprint 28 IMPLEMENTATION COMPLETE
Sprint 28 closure reconciliation IN PROGRESS
Sprint 29 NOT STARTED
```

## Disclaimer

Investment Terminal supports investment research and portfolio review. It does
not provide financial advice.

All investment decisions remain the responsibility of the investor.
