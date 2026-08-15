# Investment Terminal — Next Steps

**Current baseline:** `develop @ 1cadd3e`  
**Status:** Sprint 29 implementation complete; closure reconciliation in progress.

## Sprint 29 Closure

Provider operational accounting is now hardened beyond simple persistence.

Implemented:

```text
explicit configured ledger path
→ initialized SQLite schema
→ schema-aware readiness
→ bounded operational queries
→ exact repository summary
→ exact SQLite Decimal aggregation
→ explicit connection lifecycle
→ operational E2E
```

Operational inspection:

```text
python -m investment_terminal.cli.provider_usage_cost
```

Commands:

```text
list
recent --limit <N>
between --started-at <ISO-8601> --ended-at <ISO-8601>
show --request-id <request-id>
summary
```

`between` uses half-open semantics:

```text
[started_at, ended_at)
```

## Immediate Next Steps

```text
1. Reconcile canonical Sprint 29 documentation.
2. Reconcile project_files.txt with exact git ls-files output.
3. Run the full regression suite.
4. Commit the Sprint 29 closure baseline.
5. Perform focused post-Sprint-29 architecture/product review.
6. Select Sprint 30 only from the reconciled baseline.
```

Candidate areas for Sprint 30 review include:

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
