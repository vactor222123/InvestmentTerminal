# InvestmentTerminal AI Context

## Documentation Authority

Read root canonical documents first:

```text
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
README.md
```

Use `docs/` as synchronized supporting context. Root canonical documents win on
conflict.

## Mission

InvestmentTerminal is a private, local-first investment intelligence platform
for deterministic analysis, preserved historical evidence, traceable Knowledge,
evidence-grounded AI assistance, and reproducible controlled delivery.

## Authority Flow

```text
market / external data
→ deterministic analysis
→ Review Package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ grounded generation
→ strict grounding validation
→ ADMISSIBLE generated result
→ durable generated evidence
```

Generated evidence never becomes History or Knowledge automatically.

## Engineering Invariants

1. Reliability over cleverness.
2. Correctness before convenience.
3. Evidence before interpretation.
4. Authority flows one way.
5. History archive bytes are canonical; History SQLite is rebuildable.
6. Knowledge is explicit and evidence-backed.
7. AI provider output is untrusted until grounding validation.
8. Only ADMISSIBLE generated evidence may be persisted.
9. Persisted generated JSON is deeply immutable and strict-JSON validated.
10. Runtime operational controls fail closed.
11. Architecture dependency tests are executable contracts.
12. Dependency installation uses declared manifests and committed hash locks.
13. CI must pass from a clean checkout without developer-local data.
14. Before changing established contracts, audit consumers, fixtures,
    serialization, persistence, and composition seams.

## Delivery Contract

```text
Python 3.13.x
→ requirements-dev.lock
→ --require-hashes
→ architecture/dependency focused checks
→ full pytest
→ whitespace check
```

Canonical CI:

```text
.github/workflows/ci.yml
```

## Current Phase

```text
Sprint 31 implementation complete
closure reconciliation in progress
```

Next work begins only from the reconciled Sprint 31 baseline.
