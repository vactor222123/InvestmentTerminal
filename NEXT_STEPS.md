# Investment Terminal — Next Steps

**Current baseline:** `develop @ f95f023`  
**Status:** Sprint 27 implementation complete; closure documentation pending.

## Completed in Sprint 27

Explicit verified History-to-Knowledge ingestion is now available through:

```text
python -m investment_terminal.cli.ingest_history_knowledge
```

The operator must deliberately select either repeatable `--snapshot-id` values
or `--all`. `--dry-run` validates the same projection path without persisting a
Knowledge database mutation.

## Next Decision

Do not begin Sprint 28 by assumption.

First perform a focused post-Sprint-27 review of the repository and choose the
next milestone from current product needs and deferred scope. Candidate areas
include operational automation, deployment/infrastructure hardening, persistent
provider usage accounting, grounded answer persistence, or retrieval expansion.

The review must preserve the authority hierarchy:

```text
Archived Review Package
→ History
→ Knowledge
→ Grounded AI
```

and must not move History dependencies into Knowledge/application domain code.
