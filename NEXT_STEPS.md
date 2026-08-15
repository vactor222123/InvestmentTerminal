# Investment Terminal — Next Steps

**Current baseline:** `develop @ 3745ead`  
**Status:** Sprint 27 closed; post-Sprint-27 review in progress.

## Sprint 27 Closure

Explicit verified History-to-Knowledge ingestion is complete through:

```text
python -m investment_terminal.cli.ingest_history_knowledge
```

Operational safeguards require deliberate `--snapshot-id` selection or explicit
`--all`. `--dry-run` validates the same projection path without persistent
Knowledge mutation.

## Immediate Next Steps

```text
1. Reconcile project_files.txt with the exact tracked repository.
2. Complete post-Sprint-27 product-boundary review.
3. Select Sprint 28 from current product needs and deferred scope.
4. Begin Sprint 28 only from the reconciled baseline.
```

Candidate areas remain:

- automatic/scheduled History-to-Knowledge ingestion;
- deployment/infrastructure hardening;
- persistent provider usage/cost accounting;
- grounded answer persistence/history;
- retrieval expansion.

The review must preserve:

```text
Archived Review Package
→ History
→ Knowledge
→ Grounded AI
```

and must not move History dependencies into Knowledge/application domain code.
