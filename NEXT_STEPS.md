# Investment Terminal — Next Steps

**Current baseline:** `develop @ ab53d8e`  
**Status:** Sprint 32 Task 2 closed with green CI; Task 32.3 is next.

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
32.1 Runtime Filesystem Contract        CLOSED / b81fe98 / CI GREEN
32.2 SQLite Operational Inventory       CLOSED / ab53d8e / CI GREEN
32.3 Consistent SQLite Backup Primitive NEXT
32.4 Backup Service
32.5 Restore Validation
32.6 Backup / Restore CLI
32.7 FastAPI Lifespan Contract
32.8 Runtime Deployment Layout
32.9 Container Baseline
32.10 Deployment Security Contract
32.11 CI Container Smoke Test
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.2 Result

The repository now has an explicit executable SQLite persistence inventory:

```text
HISTORY_SQLITE@1
→ rebuildable projection
→ rebuild from upstream historical authority

KNOWLEDGE_SQLITE@1
→ rebuildable derived state
→ backup for availability

PROVIDER_USAGE_COST_SQLITE@1
→ durable operational record
→ backup required

GROUNDED_GENERATION_SQLITE@1
→ durable generated evidence
→ backup required
```

This classification is policy input for later backup/restore work.

## Current Next Action

```text
Sprint 32 Task 3 — Consistent SQLite Backup Primitive
```

Task 32.3 must implement a file-backed SQLite backup primitive with:

```text
SQLite backup API
→ WAL-safe consistent snapshot
→ temporary destination
→ validation
→ atomic publication
→ partial-output cleanup
```

Do not implement cross-database orchestration or restore activation in 32.3.
