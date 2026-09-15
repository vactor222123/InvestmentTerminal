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
`PHASE_7_PACKAGE_146_COMPLETE_COLLECTION_SWEEP_AUDIT.md`: a separate resumable
collection sweep may defer only local pre-persistence Yahoo candle validation
failures while all other failures stop progress. Implementation is the next
gate; the existing fail-fast drain remains unchanged.

`PHASE_7_PACKAGE_147_MANIFEST_COLLECTION_SWEEP.md`: implements exact checkpoint-
derived attempted coverage, non-retry resume, local-defect-only deferral,
immediate systemic halt, and the redacted collection-sweep report while leaving
the fail-fast drain unchanged.

`PHASE_7_PACKAGE_148_COLLECTION_SWEEP_HALT_RESULT.md`: records the safe batch-
106 `APIError` halt, partial transfer evidence, SQLite integrity, and the
current-run deferred-counter defect that must be audited before resume.

`PHASE_7_PACKAGE_149_SWEEP_FAILURE_EVIDENCE_AUDIT.md`: confirms lost persisted
API causality, preserves exact diagnostic guards, and selects a read-only
partial-failure qualification plus the exact deferred-counter correction.
