# Investment Terminal — Next Steps

**Current baseline:** `develop @ 2299a6f`  
**Status:** Sprint 32 Task 3 closed with green CI; Task 32.4 is next.

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
32.4 Backup Service                      NEXT
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

## 32.3 Result

The repository now owns one validated cross-domain SQLite backup primitive:

```text
known persistence boundary
→ file-backed source
→ SQLite Connection.backup()
→ WAL-safe consistent snapshot
→ PRAGMA quick_check
→ fsync
→ atomic publication
→ failure cleanup
```

Windows-specific guarantee:

```text
all SQLite handles close before replace
temp backup reopens as r+b before os.fsync
```

The Windows fix was verified by the full local regression suite:

```text
2218 passed
4 skipped
1 warning
```

and the implementation commit passed GitHub Actions.

## Current Next Action

```text
Sprint 32 Task 4 — Backup Service
```

Task 32.4 should orchestrate the three runtime-managed persistence boundaries:

```text
KNOWLEDGE_SQLITE@1
PROVIDER_USAGE_COST_SQLITE@1
GROUNDED_GENERATION_SQLITE@1
```

It must define deterministic backup-set identity/naming/metadata and explicit
partial-failure semantics.

Do not include History SQLite in the grounded-AI runtime backup set, and do not
implement restore activation in Task 32.4.
