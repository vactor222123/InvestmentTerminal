# Investment Terminal — Next Steps

**Current baseline:** `develop @ 8a22b7b`  
**Status:** Sprint 32 Task 6 closed with green CI; Task 32.7 is next.

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
32.5 Restore Validation                  CLOSED / cb8bd40 / CI GREEN
32.6 Backup / Restore CLI                CLOSED / 8a22b7b / CI GREEN
32.7 FastAPI Lifespan Contract           NEXT
32.8 Runtime Deployment Layout
32.9 Container Baseline
32.10 Deployment Security Contract
32.11 CI Container Smoke Test
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.6 Result

Runtime operator workflows now expose:

```text
backup
validate
restore
```

Restore is implemented as an offline workflow beneath the CLI:

```text
validate
→ rollback snapshots
→ staged candidates
→ WAL checkpoint
→ journal_mode DELETE
→ close handles
→ replace
→ compensating rollback on partial failure
```

The CLI requires explicit:

```text
--confirm-offline
```

A KnowledgeSQLiteStore lifecycle defect discovered by Windows restore testing
was also fixed: short-lived store helpers now explicitly close their SQLite
connections.

## Current Next Action

```text
Sprint 32 Task 7 — FastAPI Lifespan Contract
```

Task 32.7 should move production startup/shutdown resource ownership into an
explicit FastAPI lifespan boundary where appropriate, with focused coverage for
startup failure, readiness interaction, and deterministic cleanup.

Do not mix deployment layout, container work, or backup scheduling into 32.7.
