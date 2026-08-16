# Investment Terminal — Next Steps

**Current baseline:** `develop @ 543e737`  
**Status:** Sprint 32 Task 8 closed with green CI; Task 32.9 is next.

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
32.7 FastAPI Lifespan Contract           CLOSED / 3b069e6 / CI GREEN
32.8 Runtime Deployment Layout           CLOSED / 543e737 / CI GREEN
32.9 Container Baseline                  NEXT
32.10 Deployment Security Contract
32.11 CI Container Smoke Test
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.8 Result

Canonical deployment topology is now explicit:

```text
/application   read-only application/code
/runtime       persistent writable live SQLite state
/backups       persistent independent backup storage
/config        read-only non-secret configuration
/secrets       read-only deployment-managed secret boundary
```

Canonical live runtime paths:

```text
/runtime/knowledge.db
/runtime/operational/provider_usage_cost.db
/runtime/operational/grounded_generations.db
```

The deployment contract is descriptive and does not silently create, relocate,
or mutate live data.

## Current Next Action

```text
Sprint 32 Task 9 — Container Baseline
```

Task 32.9 should consume the established layout in a minimal production
container baseline:

```text
locked dependency install
non-root execution
read-only application code
persistent /runtime and /backups boundaries
healthcheck
one-worker server runtime
```

Do not mix reverse-proxy/TLS/security-topology work into 32.9; that remains
Task 32.10.
