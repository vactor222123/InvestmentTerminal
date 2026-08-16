# Investment Terminal — Next Steps

**Current baseline:** `develop @ 0b854ed`  
**Status:** Sprint 32 CLOSED; Post-Sprint-32 audit is next.

## Durable Continuation Checkpoint

Before starting or resuming implementation work, read:

```text
PROJECT_CONTINUATION.md
```

It is the canonical execution/handoff checkpoint and MUST be updated after
every completed Task or Sprint closure.

## Platform Contract

```text
Local development / host persistence regression:
Windows + PowerShell + Python 3.13

Production container execution verification:
GitHub Actions ubuntu-latest + Docker
```

These prove different properties. Linux container CI does not replace Windows
SQLite/file-handle/restore verification.

## Sprint 32 — CLOSED

Implementation closure baseline:

```text
0b854ed
```

Completed:

```text
32.1 Runtime Filesystem Contract         CLOSED / b81fe98
32.2 SQLite Operational Inventory        CLOSED / ab53d8e
32.3 Consistent SQLite Backup Primitive  CLOSED / 2299a6f
32.4 Backup Service                      CLOSED / 5e846ce
32.5 Restore Validation                  CLOSED / cb8bd40
32.6 Backup / Restore CLI                CLOSED / 8a22b7b
32.7 FastAPI Lifespan Contract           CLOSED / 3b069e6
32.8 Runtime Deployment Layout           CLOSED / 543e737
32.9 Container Baseline                  CLOSED / f0a4b64
32.10 Deployment Security Contract       CLOSED / 1c6fe62
32.11 CI Container Smoke Test            CLOSED / b4c26a7
32.12 Real Operational Resilience E2E    CLOSED / 0b854ed
32.13 Sprint 32 Closure                  CLOSED
```

Sprint 32 now provides a repository-owned production/operational baseline from
runtime filesystem ownership through real backup/restore recovery and real
container execution verification.

## Current Next Action

```text
Post-Sprint-32 audit
```

Do not start an arbitrary Sprint 33.

Audit the current repository and choose the next coherent direction based on
evidence. Specifically determine whether the highest-value next work is:

```text
additional production/security/multi-instance maturity
observability/operations
or
return to intelligence/product feature expansion
```

The next Sprint must have a concrete audited bottleneck, explicit acceptance
criteria, and explicit deferred scope.
