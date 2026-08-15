# Investment Terminal

> A private, local-first investment intelligence platform built around deterministic analysis, preserved evidence, traceable Knowledge, and evidence-grounded AI assistance.

**Status:** Active development  
**Latest completed milestone:** Sprint 27 — Explicit History-to-Knowledge Ingestion  
**Current phase:** Sprint 27 closed; post-Sprint-27 review in progress  
**Primary language:** Python

## Overview

Investment Terminal is a modular monolith for long-term investment analysis and disciplined review workflows.

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

The central engineering rule is:

> Preserve verified evidence before interpretation, keep important calculations deterministic, and make conclusions traceable to their inputs.

## Sprint 27

Sprint 27 added an explicit, deterministic ingestion boundary from verified History into Knowledge.

Canonical command:

```text
python -m investment_terminal.cli.ingest_history_knowledge
```

Operational scope is mandatory:

```text
--snapshot-id <UUID>
```

which may be repeated for an explicit batch, or:

```text
--all
```

for deliberate full-History selection.

A non-persistent validation run uses:

```text
--dry-run
```

The ingestion path preserves History/Knowledge domain separation:

```text
History models
→ CLI composition adapter
→ HistoricalSnapshotKnowledgeSource
→ Knowledge projection
→ Knowledge repository
```

Knowledge itself does not import the History package.

## Historical Evidence

Canonical historical authority:

```text
Review Package
→ immutable archived JSON
→ append-only manifest
→ verified/rebuildable SQLite History
```

Archived JSON remains canonical evidence. SQLite History is a rebuildable query projection.

Sprint 27 Knowledge records preserve exact snapshot evidence identity and archive checksum provenance.

## Grounded AI

Grounded AI continues downstream of Knowledge:

```text
Knowledge
→ GroundedPromptInput
→ provider
→ untrusted response
→ strict parser
→ grounding validation
→ admissible grounded generation
```

Provider output is not canonical historical evidence.

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

Production currently supports one worker because inbound rate-limit state is process-local.

## Provider Controls

Canonical production composition includes:

- provider/model allowlisting;
- bounded retry/resilience;
- explicit output-token limit;
- total-token budget;
- total-cost budget;
- explicit provider pricing policy;
- usage/cost accounting;
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

Historical sprint plans/reviews remain supporting records rather than current architecture authority.

## Testing

Full suite:

```powershell
python -m pytest -q
```

Every focused change should retain a green full regression suite.

## Current Deferred Scope

Not currently claimed:

- automatic/scheduled History-to-Knowledge ingestion;
- distributed/multi-worker rate-limit state;
- autonomous trading;
- broker execution;
- streaming grounded-AI responses;
- automatic provider pricing synchronization;
- persistent provider usage/cost ledger;
- grounded answer persistence/history;
- vector retrieval/embeddings.

## Current Phase

```text
Sprint 27 CLOSED
Post-Sprint-27 review IN PROGRESS
Sprint 28 NOT STARTED
```

The next milestone will be selected only after current repository inventory and product boundaries are reviewed.

## Disclaimer

Investment Terminal supports investment research and portfolio review. It does not provide financial advice.

All investment decisions remain the responsibility of the investor.
