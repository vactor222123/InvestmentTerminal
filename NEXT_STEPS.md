# Investment Terminal — Next Steps

**Current baseline:** `develop @ 17a7fe1`  
**Status:** Sprint 30 implementation complete; closure reconciliation in progress.

## Sprint 30 Closure

Grounded generations are now durable generated evidence.

Implemented:

```text
ADMISSIBLE typed generation
→ deterministic persistence projection
→ immutable repository identity
→ grounded_generations.db
→ runtime composition
→ schema-aware readiness
→ bounded queries
→ operational CLI
→ authenticated HTTP read API
→ close/reopen/readback E2E
```

Operational inspection:

```text
python -m investment_terminal.cli.grounded_generations
```

Read-only HTTP inspection:

```text
GET /v1/grounded-generations?limit=<N>
GET /v1/grounded-generations/{request_id}
```

Generated evidence remains downstream of Knowledge and is never automatically
promoted into Knowledge or History.

## Immediate Next Steps

```text
1. Reconcile canonical Sprint 30 documentation.
2. Reconcile project_files.txt with exact git ls-files output.
3. Run the full regression suite.
4. Commit and push the Sprint 30 closure baseline.
5. Perform focused post-Sprint-30 architecture/product review.
6. Select Sprint 31 only from the reconciled baseline.
```

## Post-Sprint-30 Audit Candidates

Candidate areas include:

- automatic/scheduled History-to-Knowledge ingestion;
- deployment/infrastructure hardening;
- distributed rate-limit state;
- authorization beyond a single API-key boundary;
- provider request/response archival policy;
- semantic retrieval expansion;
- contradiction/entailment analysis;
- explicit governance for any future generated-evidence promotion workflow.

The audit must preserve:

```text
Archived Review Package
→ History
→ explicit ingestion
→ Knowledge
→ Grounded AI
→ persisted generated evidence
```

Provider usage/cost data remains parallel operational accounting.
