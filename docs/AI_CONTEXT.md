# InvestmentTerminal AI Context

## Documentation Authority

Before major changes, read the root canonical documents first:

```text
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
README.md
```

Then use this file and other `docs/` material as supporting context. If they
conflict, the root canonical document wins.

## Mission

InvestmentTerminal is a private, local-first investment intelligence platform
for deterministic analysis, preserved historical evidence, traceable Knowledge,
evidence-grounded AI assistance, and explicit operational accounting.

## Current Authority Flow

```text
market / external data
→ analysis
→ review package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ grounded prompt/context
→ provider execution
→ strict parsing
→ grounding validation
→ ADMISSIBLE generated result
→ durable generated evidence
```

Generated evidence does not become canonical History or Knowledge automatically.

Parallel provider accounting remains operational only.

## Important Boundaries

### History

History owns immutable archived evidence and rebuildable historical projections.
It must not depend on downstream Knowledge, AI, application, API, or server
layers.

### Knowledge

Knowledge owns versioned evidence-backed records. It is upstream of grounded AI
and cannot mutate History.

### Grounded AI

Grounded AI consumes Knowledge, validates provider output, and may persist only
ADMISSIBLE generated evidence.

Persisted generation and trace JSON is deeply immutable and strict-JSON
validated.

### Application / API

Application services orchestrate AI and Knowledge contracts. Framework-neutral
API mapping stays outside domain-rule ownership.

### Production Server

Canonical runtime:

```text
investment_terminal.server.production:create_app
```

Canonical CLI:

```text
python -m investment_terminal.cli.server
```

Runtime endpoints:

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations
GET  /v1/grounded-generations/{request_id}
```

## Runtime Persistence

Distinct responsibilities use distinct stores:

```text
Knowledge database
History projection database
provider usage/cost database
grounded-generation database
```

Do not collapse these into one authority model.

## Engineering Rules

1. Reliability over cleverness.
2. Correctness before convenience.
3. Deterministic ordering and explicit contracts.
4. Preserve evidence before interpretation.
5. Keep authority direction one-way.
6. CLI/server layers do not own domain rules or SQL.
7. Provider responses are untrusted before grounding validation.
8. Persist only ADMISSIBLE generated evidence.
9. Persisted temporal values are timezone-aware.
10. Runtime controls fail closed when required configuration/integrity checks
    fail.
11. Architecture dependency tests are part of the contract.
12. Before changing an established contract, audit direct consumers,
    fixtures, serialization, composition seams, and persistence assumptions.

## Current Sprint

```text
Sprint 31 — Evidence Integrity & Delivery Hardening
```

Completed so far:

- true deep immutability for persisted grounded evidence;
- strict JSON persistence validation;
- modern dependency/authority guards.

Current work is documentation/environment reconciliation, followed by
reproducibility and CI hardening.
