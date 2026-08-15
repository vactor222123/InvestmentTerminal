# Investment Terminal

> A private, local-first investment intelligence platform built around deterministic analysis, preserved evidence, traceable Knowledge, evidence-grounded AI assistance, and explicit operational accounting.

**Status:** Active development  
**Latest completed implementation milestone:** Sprint 29 — Provider Operational Accounting Hardening  
**Current phase:** Sprint 29 closure reconciliation  
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

Parallel operational accounting:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
→ bounded operational queries
→ exact summaries
```

That ledger is operational evidence only. It does not become canonical History or
Knowledge.

## Sprint 29

Sprint 29 hardens the operational accounting boundary.

Implemented:

- explicit ledger runtime path;
- production schema initialization;
- schema-aware readiness;
- bounded recent/time-window queries;
- bounded operational CLI commands;
- repository-owned summaries;
- exact single-query SQLite Decimal aggregation;
- exact high-precision cost preservation;
- explicit SQLite connection lifecycle;
- real operational E2E.

Operational CLI:

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

Readiness now includes:

```text
knowledge_database
provider_usage_cost_database
provider_credentials
```

The ledger readiness check validates the supported schema version and fails
closed for missing, uninitialized, corrupt, or incompatible storage.

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
- explicit ledger runtime path;
- schema-aware ledger readiness;
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
Sprint 29 IMPLEMENTATION COMPLETE
Sprint 29 closure reconciliation IN PROGRESS
Sprint 30 NOT STARTED
```

## Disclaimer

Investment Terminal supports investment research and portfolio review. It does
not provide financial advice.

All investment decisions remain the responsibility of the investor.
