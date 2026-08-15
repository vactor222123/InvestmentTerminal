# Investment Terminal — Next Steps

**Current baseline before Sprint 31 closure docs:** `develop @ c3d307f`  
**Status:** Sprint 31 implementation complete; closure reconciliation in progress.

## Sprint 31 Closure

Sprint 31 hardened both evidence integrity and software delivery.

Implemented:

```text
deep immutable generated evidence
→ strict JSON persistence boundary
→ expanded architecture dependency guards
→ single documentation authority hierarchy
→ Python 3.13.x reproducibility contract
→ source dependency manifests
→ hash-locked dependencies
→ cross-platform lock installation
→ GitHub Actions CI
→ hermetic clean-clone tests
```

The CI quality gate now proves:

```text
locked dependency install
→ dependency contract tests
→ architecture dependency tests
→ full pytest
→ whitespace validation
```

The clean Linux CI run for `c3d307f` completed successfully.

## Immediate Closure Steps

```text
1. Reconcile canonical and supporting Sprint 31 documentation.
2. Regenerate project_files.txt from exact git ls-files output.
3. Run the full regression suite.
4. Commit and push the Sprint 31 closure baseline.
5. Confirm the closure commit passes GitHub Actions.
6. Perform a focused post-Sprint-31 architecture/product audit.
7. Select Sprint 32 only from the reconciled baseline.
```

## Post-Sprint-31 Audit Candidates

The strongest remaining candidate areas are:

- production deployment/infrastructure contract;
- backup/restore and operational SQLite lifecycle;
- authorization beyond one API key;
- shared/distributed rate limiting;
- provider request/response archival policy;
- scheduled History-to-Knowledge ingestion;
- semantic retrieval expansion;
- contradiction/entailment analysis;
- explicit governance for generated-evidence promotion.

The next sprint should preserve:

```text
History
→ explicit Knowledge ingestion
→ Knowledge
→ Grounded AI
→ persisted generated evidence
```

and the delivery baseline:

```text
declared dependencies
→ hash locks
→ clean CI
→ architecture guards
→ full regression
```
