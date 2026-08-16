# Investment Terminal — Next Steps

**Current baseline:** `develop @ cb8bd40`  
**Status:** Sprint 32 Task 5 closed with green CI; Task 32.6 is next.

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
32.6 Backup / Restore CLI                NEXT
32.7 FastAPI Lifespan Contract
32.8 Runtime Deployment Layout
32.9 Container Baseline
32.10 Deployment Security Contract
32.11 CI Container Smoke Test
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.5 Result

Runtime restore validation now performs:

```text
backup-set metadata validation
→ exact runtime boundary membership
→ inventory classification validation
→ exact file mapping
→ size validation
→ read-only immutable SQLite quick_check
→ required tables
→ schema metadata/version compatibility
→ validated restore candidate
```

Validation does not initialize or mutate live databases.

Windows/SQLite lessons retained:

```text
SQLite-managed WAL/SHM sidecars may exist around backup lifecycle operations
stage-specific tests must snapshot immediately before the stage under test
```

## Current Next Action

```text
Sprint 32 Task 6 — Backup / Restore CLI
```

Task 32.6 must keep CLI thin. It should orchestrate the existing backup and
validation/application services, not own SQLite internals or raw filesystem
replacement.

Before implementing restore activation through CLI, audit whether a dedicated
restore-activation service is required beneath the CLI to preserve this
boundary.
