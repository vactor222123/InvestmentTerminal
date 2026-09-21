# Phase 7 Package 167 — Timeout Retry Execution Rebaseline

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ f3ed7bac471f598fc368d4a1b309fc4982c16848
```

## Audit Result

Package 166 was committed and pushed before its user-executed timeout retry was
run. Its PowerShell block correctly rejects the newer repository HEAD because
the block was bound to the Package 165 baseline. No redacted retry report has
been returned, so collection resume remains unauthorized.

The smallest safe correction changes only the command's exact expected HEAD to
the Package 166 GitHub commit. The manifest, request, inventory, batch, report,
checkpoint, SQLite, and causal-signature bindings remain byte-for-byte
unchanged. The command still invokes exactly one
`manifest_partial_timeout_retry` operation and never invokes the collection
sweep.

The complete rebaselined ASCII-only command remains in
`docs/PHASE_7_PACKAGE_166_PARTIAL_TIMEOUT_RETRY_HANDOFF.md` so there is only one
operator block to copy.

## Scope Exclusions

- no private runtime input was read or changed in this package;
- no Yahoo request, timeout retry, SQLite write, or sweep was executed;
- no JSON, checkpoint, database, architecture, or dependency contract changed;
- no authorization to process the two missing batch members or later batches;
- no analysis, ranking, recommendation, or trading authority.

## Repository Verification

```text
PowerShell rebaseline validation: passed (483 lines)
focused timeout-retry, causal-inventory, sweep, resumable-batch, manifest, and
architecture tests: 81 passed in 3.52s
full test suite: 3146 passed, 4 skipped, 1 warning in 32.35s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 167 regression.

## Next Gate

Run the rebaselined block once before applying Package 167. Return only
`C:\runtime\reports\manifest_batch_0576_timeout_retry_001.json` and the printed
`SQLite integrity: ok` line. Do not resume the collection sweep until the
redacted retry disposition is reviewed.
