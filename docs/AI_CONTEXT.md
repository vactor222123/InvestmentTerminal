# InvestmentTerminal AI Context

## Resume / Handoff First

For any continuation of implementation work, read:

```text
PROJECT_CONTINUATION.md
```

first, then verify its recorded baseline against the current `develop` HEAD.

`PROJECT_CONTINUATION.md` is the canonical execution/handoff checkpoint and
MUST be updated after every completed Task.

## Documentation Authority

Read root canonical documents:

```text
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
README.md
```

Use `docs/` as synchronized supporting context. Root canonical documents win on
architecture/product conflict.

`PROJECT_CONTINUATION.md` does not replace Architecture/DataModel authority; it
owns current execution state, audit path, failure lessons, and next action.

AI-assisted package preparation and user-executed runtime handoffs additionally
follow:

```text
docs/AI_ASSISTED_DELIVERY_WORKFLOW.md
```

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
15. Update `PROJECT_CONTINUATION.md` after every completed Task.

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
Sprint 31 CLOSED
post-Sprint-31 audit complete
audit-driven hardening / production maturity
Sprint 32 selected
```

Current next action:

```text
Sprint 32 Task 1 — Runtime Filesystem Contract
```

Read `PROJECT_CONTINUATION.md` for the detailed audit, Sprint 32 plan, working
protocol, and resume instructions.
