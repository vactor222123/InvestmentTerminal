# Investment Terminal — Next Steps

**Current baseline:** `develop @ 30a28ac`  
**Status:** Durable continuation checkpoint established and CI-verified; Sprint 32 ready to begin.

## Durable Continuation Checkpoint

Before starting or resuming implementation work, read:

```text
PROJECT_CONTINUATION.md
```

It is the canonical execution/handoff checkpoint and records the verified
baseline, current phase, audit findings, approved Sprint plan, failure lessons,
working protocol, and exact next Task.

`PROJECT_CONTINUATION.md` MUST be updated after every completed Task.

Checkpoint baseline:

```text
develop @ 30a28ac
CI: GREEN
```

## Sprint 31

Sprint 31 — Evidence Integrity & Delivery Hardening — is CLOSED.

Established:

```text
deep immutable generated evidence
→ strict JSON persistence boundary
→ expanded architecture dependency guards
→ documentation authority hierarchy
→ Python 3.13.x reproducibility contract
→ source dependency manifests
→ hash-locked dependencies
→ cross-platform lock installation
→ GitHub Actions CI
→ hermetic clean-clone tests
```

## Post-Sprint-31 Audit Result

The strongest current gap is no longer evidence correctness or reproducible
delivery.

The next production-maturity gap is:

```text
runtime filesystem ownership
→ SQLite operational lifecycle
→ backup / restore
→ explicit application lifespan
→ deployment layout
→ container baseline
→ operational resilience E2E
```

## Sprint 32

Selected:

```text
Sprint 32 — Production Deployment & Operational Resilience
```

The detailed approved 32.1–32.13 plan is maintained in
`PROJECT_CONTINUATION.md`.

## Current Next Action

```text
Sprint 32 Task 1 — Runtime Filesystem Contract
```

Do not begin with Docker. First define persistent state, path ownership,
compatibility, and filesystem invariants.

## Preserved Authority

```text
History
→ explicit Knowledge ingestion
→ Knowledge
→ Grounded AI
→ persisted generated evidence
```

Delivery baseline:

```text
declared dependencies
→ hash locks
→ clean CI
→ architecture guards
→ full regression
```
