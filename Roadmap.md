# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 31 — Evidence Integrity & Delivery Hardening  
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
→ Evidence Integrity & Reproducible Delivery
```

## Recent Completed Milestones

### Sprint 27 — Explicit History-to-Knowledge Ingestion

Verified deterministic History → Knowledge ingestion, exact evidence/checksum
preservation, idempotent immutable versions, dry-run validation, and real E2E.

### Sprint 28 — Persistent Provider Usage & Cost Ledger

Added immutable provider-neutral usage/cost accounting with dedicated SQLite
persistence and operational CLI.

### Sprint 29 — Provider Operational Accounting Hardening

Added runtime-configured ledger path, schema-aware readiness, bounded queries,
exact Decimal summary aggregation, connection lifecycle hardening, and real
operational E2E.

### Sprint 30 — Grounded Generation Persistence & History

Added immutable generated-evidence persistence, runtime composition, readiness,
bounded queries, CLI/HTTP inspection, and real durable Knowledge → generation →
persistence → reopen/readback E2E.

### Sprint 31 — Evidence Integrity & Delivery Hardening

Delivered:

- true deep immutability for persisted grounded generation/trace JSON;
- strict JSON value validation;
- fail-closed rejection of non-finite numbers and non-string object keys;
- detached serialization and strict SQLite JSON persistence;
- expanded executable architecture dependency/authority guards;
- explicit documentation authority hierarchy;
- complete environment contract for grounded-generation persistence;
- Python 3.13.x dependency-resolution baseline;
- separate runtime/dev dependency source manifests;
- pinned dependency compiler toolchain;
- hash-locked runtime and development dependency artifacts;
- cross-platform dependency ownership without hidden `fastapi[standard]` extras;
- first GitHub Actions quality gate;
- locked Linux CI installation;
- dependency and architecture contract checks in CI;
- full regression suite in CI;
- whitespace gate;
- hermetic portfolio/review tests that no longer depend on a developer-local
  personal portfolio file.

Sprint 31 closes with both local and clean Linux CI regression suites green.

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

Generated evidence remains downstream and is not automatically promoted into
History or Knowledge.

Parallel operational accounting remains:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
→ bounded operational queries / exact summaries
```

## Delivery Integrity Baseline

Repository delivery now includes:

```text
Python 3.13.x
→ declared direct dependencies
→ pinned resolver/compiler toolchain
→ hash-locked dependency artifacts
→ clean Linux CI install
→ architecture contract tests
→ full pytest
→ git diff --check
```

Canonical CI workflow:

```text
.github/workflows/ci.yml
```

## Deferred Scope

Still deferred:

- automatic/scheduled History-to-Knowledge ingestion;
- shared/distributed rate-limit state;
- deployment container/image and infrastructure manifests;
- backup/restore operational contract;
- TLS termination/HSTS deployment policy;
- authorization beyond API-key authentication;
- retry jitter;
- proactive/concurrency-aware provider throttling;
- streaming responses;
- additional provider adapters;
- provider pricing synchronization;
- semantic entailment/contradiction detection;
- vector retrieval/embeddings;
- generated-evidence promotion governance;
- autonomous portfolio actions;
- broker execution.

## Current Decision Point

Phases 1–5 of the post-audit product roadmap are complete. The Phase 6
Integrated Investment Review Workflow boundary audit is recorded in
`docs/PHASE_6_WORKFLOW_BOUNDARY_AUDIT.md` at verified baseline
`89c3a706cd425c0fbe85e5321c841d297a2260ee`. Packages 1–2 now establish the
immutable workflow run contract and typed deterministic evidence aggregate.

Next:

```text
Phase 6 Package 1 — immutable workflow run contract — COMPLETE
→ Phase 6 Package 2 — typed evidence assembly — COMPLETE
→ Phase 6 Package 3 — Review export
→ History preservation/projection
→ historical comparison
→ user-facing review command
```

## Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes locally;
- clean CI regression suite passes;
- architecture boundaries remain clean;
- dependency installation is reproducible;
- documentation reflects implementation;
- deferred scope is explicit;
- repository inventory is reconciled;
- repository is committed and pushed.
