# Investment Terminal — Next Steps

**Current baseline:** `develop @ 5e846ce`  
**Status:** Sprint 32 Task 4 closed with green CI; Task 32.5 is next.

## Durable Continuation Checkpoint

Before starting or resuming implementation work, read:

```text
PROJECT_CONTINUATION.md
```

It is the canonical execution/handoff checkpoint and MUST be updated after
every completed Task.

## Sprint 32 — Production Deployment & Operational Resilience

Progress:

```text
32.1 Runtime Filesystem Contract         CLOSED / b81fe98 / CI GREEN
32.2 SQLite Operational Inventory        CLOSED / ab53d8e / CI GREEN
32.3 Consistent SQLite Backup Primitive  CLOSED / 2299a6f / CI GREEN
32.4 Backup Service                      CLOSED / 5e846ce / CI GREEN
32.5 Restore Validation                  NEXT
32.6 Backup / Restore CLI
32.7 FastAPI Lifespan Contract
32.8 Runtime Deployment Layout
32.9 Container Baseline
32.10 Deployment Security Contract
32.11 CI Container Smoke Test
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.4 Result

Runtime backup orchestration now creates one complete backup set for exactly:

```text
KNOWLEDGE_SQLITE@1
PROVIDER_USAGE_COST_SQLITE@1
GROUNDED_GENERATION_SQLITE@1
```

History SQLite is intentionally excluded.

Set publication is:

```text
explicit backup_root
→ deterministic UTC set identity
→ staging directory
→ three WAL-safe SQLite backups
→ deterministic metadata.json
→ atomic directory publication
→ backup-root sync
```

A pre-publication failure leaves no final backup set.

## Current Next Action

```text
Sprint 32 Task 5 — Restore Validation
```

Task 32.5 must validate a complete restore candidate before any live database
mutation. It must fail closed on malformed metadata, missing/extra/wrong
boundaries, corrupt SQLite files, and incompatible schema/version.

Do not activate or overwrite live databases in Task 32.5.
