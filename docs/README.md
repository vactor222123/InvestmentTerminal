# Investment Terminal Documentation

## Documentation Authority

Canonical repository-level authority:

```text
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
README.md
CHANGELOG.md
```

The `docs/` directory contains supporting synchronized architecture,
domain-context, operational, and historical material.

Root canonical documents are authoritative if a conflict appears.

## Current Product State

```text
Sprint 31 — Evidence Integrity & Delivery Hardening — IMPLEMENTATION COMPLETE
Closure reconciliation in progress
```

Current authority flow:

```text
Review Package
→ immutable History
→ explicit verified ingestion
→ Knowledge
→ Grounded AI
→ ADMISSIBLE generated evidence
→ durable grounded-generation persistence
```

## Current Delivery Contract

```text
Python 3.13.x
→ direct dependency manifests
→ pinned dependency compiler
→ hash-locked dependency files
→ clean Linux GitHub Actions install
→ dependency contract checks
→ architecture guards
→ full pytest
→ whitespace gate
```

Supporting operational documentation:

```text
docs/DEPENDENCY_REPRODUCIBILITY.md
docs/CI.md
docs/AI_ASSISTED_DELIVERY_WORKFLOW.md
```

## Production Surface

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations?limit=<N>
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

## Next

After Sprint 31 documentation/inventory closure and a green closure CI run, the
project should perform a focused architecture/product audit before selecting
Sprint 32.

Current Phase 7 continuation is recorded in
`PHASE_7_PACKAGE_142_BATCHES_42_66_DRAIN_RESULT.md`: one bounded drain completed
batches 42–66 and inserted 655,813 candles without failures, duplicates, or
omissions while SQLite integrity remained `ok`. The next gate is one existing
25-batch-bounded drain beginning at batch 67.
