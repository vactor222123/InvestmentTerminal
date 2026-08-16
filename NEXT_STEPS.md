# Investment Terminal — Next Steps

**Current baseline:** `develop @ 1c6fe62`  
**Status:** Sprint 32 Task 10 closed with green CI; Task 32.11 is next.

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
32.10 Deployment Security Contract       CLOSED / 1c6fe62 / CI GREEN
32.11 CI Container Smoke Test            NEXT
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.10 Result

Canonical production security boundary is now explicit:

```text
public client
→ HTTPS
→ reverse proxy / platform ingress
→ private HTTP
→ Investment Terminal container
```

Key invariants:

```text
TLS/HSTS owned by ingress
proxy_headers=False
API-key auth remains mandatory on /v1/*
/ready and /openapi.json are deployment-private
secrets enter through process environment only
```

## Current Next Action

```text
Sprint 32 Task 11 — CI Container Smoke Test
```

Task 32.11 must close the still-unverified container execution gap:

```text
docker build
→ run container with fixture runtime mount
→ /health liveness
→ /ready readiness
→ clean shutdown and logs on failure
```

Do not call the external AI provider in this smoke test.
