# Investment Terminal — Next Steps

**Current baseline:** `develop @ b81fe98`  
**Status:** Sprint 32 Task 1 closed with green CI; Task 32.2 is next.

## Durable Continuation Checkpoint

Before starting or resuming implementation work, read:

```text
PROJECT_CONTINUATION.md
```

It is the canonical execution/handoff checkpoint and MUST be updated after
every completed Task.

## Sprint 31

Sprint 31 — Evidence Integrity & Delivery Hardening — is CLOSED.

## Sprint 32 — Production Deployment & Operational Resilience

Progress:

```text
32.1 Runtime Filesystem Contract       CLOSED / b81fe98 / CI GREEN
32.2 SQLite Operational Inventory      NEXT
32.3 Consistent SQLite Backup Primitive
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

### 32.1 Result

The production runtime now supports an optional strict data-root contract.
Existing explicit database paths are not silently relocated. When the root is
configured, production fails closed if runtime database paths escape it.

## Current Next Action

```text
Sprint 32 Task 2 — SQLite Operational Inventory
```

Task 32.2 must inventory and classify SQLite persistence before any generic
backup primitive is implemented.

The audit must distinguish canonical, operational, and rebuildable/projection
state and record ownership, criticality, rebuildability, write behavior, and
backup/restore requirements.

Do not implement backup/restore in Task 32.2.
