# Investment Terminal — Next Steps

**Current baseline:** `develop @ cffc060`  
**Status:** Sprint 28 implementation complete; closure reconciliation in progress.

## Sprint 28 Closure

Persistent provider usage/cost accounting is implemented through an immutable,
provider-neutral ledger backed by SQLite.

Operational inspection:

```text
python -m investment_terminal.cli.provider_usage_cost
```

Commands:

```text
list
show --request-id <request-id>
summary
```

Production successful priced provider usage is durably recorded without changing
History, Knowledge, grounding, or provider execution authority.

## Immediate Next Steps

```text
1. Reconcile canonical Sprint 28 documentation.
2. Reconcile project_files.txt with exact git ls-files output.
3. Run the full regression suite.
4. Commit the Sprint 28 closure baseline.
5. Perform focused post-Sprint-28 architecture/product review.
6. Select Sprint 29 only from the reconciled baseline.
```

Remaining candidate areas include:

- automatic/scheduled History-to-Knowledge ingestion;
- deployment/infrastructure hardening;
- grounded answer persistence/history;
- provider request/response persistence;
- retrieval expansion;
- distributed rate-limit state.

The review must preserve:

```text
Archived Review Package
→ History
→ Knowledge
→ Grounded AI
```

Provider usage/cost ledger data remains operational accounting, not canonical
historical investment evidence.
