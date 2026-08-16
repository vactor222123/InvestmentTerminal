# Investment Terminal — Next Steps

**Current baseline:** `develop @ b4c26a7`  
**Status:** Sprint 32 Task 11 closed with green CI; Task 32.12 is next.

## Durable Continuation Checkpoint

Before starting or resuming implementation work, read:

```text
PROJECT_CONTINUATION.md
```

It is the canonical execution/handoff checkpoint and MUST be updated after
every completed Task.

## Platform Contract

```text
Local development / regression:
Windows + PowerShell + Python 3.13

Production container verification:
GitHub Actions ubuntu-latest + Docker
```

Linux container CI does not replace Windows compatibility. Persistence,
backup/restore, SQLite WAL, file replacement, handle closing, and fsync behavior
must remain valid on Windows.

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
32.10 Deployment Security Contract       CLOSED / 1c6fe62 / CI GREEN
32.11 CI Container Smoke Test            CLOSED / b4c26a7 / CI GREEN
32.12 Real Operational Resilience E2E    NEXT
32.13 Sprint 32 Closure
```

## 32.11 Result

GitHub Actions run #27 verified the real production image:

```text
docker build                          PASS
docker run                            PASS
/health                               PASS
/ready                                PASS
non-root runtime                      PASS
operational SQLite initialization     PASS
cleanup                               PASS
Python regression job                 PASS
```

This closes the unverified Docker build/start item from Task 32.9.

## Current Next Action

```text
Sprint 32 Task 12 — Real Operational Resilience E2E
```

Required proof:

```text
write real durable runtime state
→ backup
→ validate
→ mutate/damage live state
→ offline restore
→ reopen/restart stores
→ exact pre-backup readback
```

The E2E must cover all three runtime-managed SQLite boundaries and must be
Windows-compatible. Do not introduce POSIX-only filesystem assumptions.
