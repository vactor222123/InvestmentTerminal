# Phase 6 — Integrated Investment Review Workflow Closure

## Verified baseline

`develop @ 259077314cb3ad6790fde59243fd8c3c28299bb8`

## Closure status

```text
CLOSED
```

## Roadmap scope

| Scope | Implemented evidence |
|---|---|
| Workflow run contract | Immutable, versioned `InvestmentReviewWorkflowRun` and canonical stage outcomes with dependencies, artifacts, warnings, failures, and skips |
| Deterministic evidence assembly | Typed current portfolio, ready current-state market, Phase 4 context/sentiment, and Phase 5 discovery evidence with explicit optional gaps |
| Review generation | Existing Review schema and adapters plus atomic integrated Review Package export |
| Immutable History | Archive/manifest registration remains canonical and is reported separately from rebuildable SQLite projection |
| Historical comparison | Deterministic previous compatible imported snapshot selection with completed, first-run, and unavailable outcomes |
| User-facing workflow | `python -m investment_terminal.cli.review` executes the integrated deterministic workflow and writes the versioned report |
| Failure reporting | Completed artifacts, the first failed stage, dependent skips, and archive success before projection failure are durably reported before non-zero exit |

## Remediation verification

The initial closure-readiness audit found that operational failure exited before
the workflow report was written. The bounded remediation is present at this
baseline.

Hermetic tests verify:

- a successful first run with explicit no-previous-snapshot outcome;
- a successful second run with read-only historical comparison;
- validation failure after completed refresh with all dependent stages skipped;
- projection failure after canonical archive registration with
  `ARCHIVE_HISTORY=COMPLETED`, `PROJECT_HISTORY=FAILED`, and
  `COMPARE_CHANGES=SKIPPED`;
- atomic workflow-report persistence before the CLI exits non-zero.

The blocking finding in `docs/PHASE_6_CLOSURE_AUDIT.md` is resolved.

## Authority conclusion

Orchestration coordinates existing owners and does not recalculate analytical
evidence. Review generation does not persist History. Archive registration is
the canonical historical authority; SQLite remains rebuildable. Comparison is
read-only and uses compatible imported snapshots only.

Optional runtime evidence remains explicit when no source is configured. The
workflow does not promote History into Knowledge, invoke grounded AI, access a
broker, execute a trade, or grant human-decision authority.

## Verification

The focused Phase 6 contract, integration, importer, architecture, persistence,
success-path, and failure-path suite passes: 66 passed.

The complete local suite passes: 2681 passed, 4 skipped. The only warning is the
existing Starlette `httpx` deprecation warning.

Every audited Phase 6 roadmap item and failure rule is represented by an
implemented contract, typed service, user-facing composition root, or hermetic
test. Phase 6 is closed.

The next roadmap phase is Phase 7 — User Product Layer. Its first action is a
focused boundary audit before selecting the smallest implementation package.
