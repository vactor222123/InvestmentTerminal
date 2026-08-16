# Investment Terminal — Next Steps

**Current baseline:** `develop @ 3b069e6`  
**Status:** Sprint 32 Task 7 closed with green CI; Task 32.8 is next.

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
32.8 Runtime Deployment Layout           NEXT
32.9 Container Baseline
32.10 Deployment Security Contract
32.11 CI Container Smoke Test
32.12 Real Operational Resilience E2E
32.13 Sprint 32 Closure
```

## 32.7 Result

Production construction and startup are now separate:

```text
create_app()
→ config + object composition only

ASGI lifespan startup
→ runtime filesystem prepare
→ provider usage/cost DB initialize
→ grounded-generation DB initialize
→ serve requests
```

Startup failures fail closed.

Knowledge remains an external prerequisite.

Production tests that rely on startup state now use:

```python
with TestClient(app) as client:
    ...
```

## Current Next Action

```text
Sprint 32 Task 8 — Runtime Deployment Layout
```

Task 32.8 should define the concrete deployment topology for:

```text
read-only application/code
writable persistent runtime data
backup destination
configuration boundary
secret boundary
```

Do not introduce Docker yet. Task 32.9 should consume the layout contract rather
than invent it.
