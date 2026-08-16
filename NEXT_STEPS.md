# Investment Terminal — Next Steps

**Current baseline:** `develop @ f0a4b64`  
**Status:** Sprint 32 Task 9 closed with green CI; Task 32.10 is next.

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
32.9 Container Baseline                  CLOSED / f0a4b64 / CI GREEN
32.10 Deployment Security Contract       NEXT
32.11 CI Container Smoke Test
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.9 Result

Production container baseline now defines:

```text
python:3.13-slim
hash-locked runtime dependency install
non-root execution
read-only /application
persistent /runtime and /backups
healthcheck on /health
one-worker server runtime
```

Local Python/contract regression was green.

Important verification note:

```text
local docker build NOT executed
reason: Docker CLI unavailable
real image build/start verification: Task 32.11
```

## Current Next Action

```text
Sprint 32 Task 10 — Deployment Security Contract
```

Task 32.10 should define:

```text
reverse-proxy trust boundary
TLS termination ownership
secret injection ownership
trusted-network assumptions
forwarded-header assumptions
public/private endpoint exposure
```

Keep actual container build/start CI work in 32.11.
