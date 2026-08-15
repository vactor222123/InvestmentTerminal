# Investment Terminal

> Professional private investment intelligence system

## Overview

Investment Terminal is a modular Python application for deterministic investment
analysis, immutable historical evidence, explicit Knowledge construction,
evidence-grounded AI, and controlled production delivery.

The system is built around six non-negotiable properties:

- correctness;
- determinism;
- traceability;
- historical integrity;
- explicit authority boundaries;
- explicit human decision ownership.

The Python engine produces canonical calculations and evidence. AI may interpret
approved Knowledge, but it does not replace archived facts, canonical
calculations, or the investor's final decision.

## Authority Hierarchy

```text
Current-state deterministic analysis
→ Review Package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ GroundedPromptInput
→ provider execution
→ grounding validation
→ ADMISSIBLE GroundedGenerationResult
→ persisted generated evidence
```

Persisted grounded generations remain downstream generated evidence. They are
not automatically promoted into History or Knowledge.

Parallel operational accounting:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
→ bounded operational queries / exact summaries
```

The provider ledger is operational accounting, not canonical investment
evidence.

## Current Product Capabilities

### Current-state intelligence

- market-data acquisition and validation;
- technical and fundamental analysis;
- ranking and machine recommendations;
- portfolio holdings and policy;
- cost-basis and market-value portfolio views;
- contribution and deployment planning;
- versioned Review Package generation.

### Historical intelligence

- immutable exact-byte Review Package archive;
- SHA-256 verification;
- append-only archive manifest;
- SQLite historical projection;
- schema migrations;
- explicit import state;
- atomic detail import;
- timeline and navigation queries;
- snapshot comparison;
- exact and normalized historical replay.

### Knowledge

- immutable/versioned Knowledge records;
- exact evidence references;
- deterministic SQLite persistence and queries;
- explicit verified History-to-Knowledge ingestion;
- dry-run ingestion;
- idempotent identity semantics;
- read-only operational inspection.

### Evidence-grounded AI

- provider-neutral grounded prompt and answer protocols;
- deterministic Knowledge selection;
- strict provider response parsing;
- exact Knowledge citation validation;
- ADMISSIBLE/REJECTED grounding validation;
- auditable generation trace;
- provider governance and budget controls;
- immutable persistence of ADMISSIBLE grounded generations;
- bounded generation history queries;
- read-only CLI inspection;
- authenticated read-only HTTP history API;
- real durable end-to-end persistence/readback coverage.

### Production runtime

Canonical factory:

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
GET  /v1/grounded-generations?limit=<N>
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

The production runtime includes API-key authentication, request-size controls,
rate limiting, sanitized errors, provider governance, pricing/budget controls,
persistent provider accounting, persistent grounded-generation evidence, and
schema-aware readiness.

## Operational CLIs

History:

```text
python -m investment_terminal.cli.import_history
python -m investment_terminal.cli.query_history
python -m investment_terminal.cli.compare_history
python -m investment_terminal.cli.replay_history
```

Knowledge:

```text
python -m investment_terminal.cli.knowledge
python -m investment_terminal.cli.ingest_history_knowledge
```

Provider usage/cost accounting:

```text
python -m investment_terminal.cli.provider_usage_cost
```

Grounded-generation inspection:

```text
python -m investment_terminal.cli.grounded_generations
```

All inspection CLIs are read-only boundaries.

## Historical Source-of-Truth Rule

```text
Archived Review Package JSON
    canonical historical evidence

manifest.jsonl
    append-only navigation index

history.db
    rebuildable structured projection
```

SQLite historical projections may be rebuilt. Archived Review Package bytes
must not be rewritten.

## Testing

The repository contains deterministic network-free end-to-end fixtures for
History, History-to-Knowledge ingestion, provider accounting, and grounded
generation persistence.

Sprint 30 adds a real durable flow covering:

```text
Knowledge SQLite
→ grounded generation
→ ADMISSIBLE validation
→ grounded_generations.db
→ close/reopen
→ authenticated exact/recent HTTP readback
```

## Project Philosophy

**Data Quality First. Evidence Before Narrative. History Is Immutable.
Authority Must Be Explicit.**

The application must never fabricate unavailable data, hide uncertainty,
silently reinterpret historical evidence, or promote generated AI output into
canonical evidence without an explicit future authority transition.

## Disclaimer

Investment Terminal is research and decision-support software. It does not
provide financial advice and does not execute trades. The investor remains
responsible for every investment decision.
