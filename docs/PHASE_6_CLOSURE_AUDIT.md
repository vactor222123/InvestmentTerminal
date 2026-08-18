# Phase 6 — Integrated Investment Review Workflow Closure Audit

## Verified baseline

`develop @ 0212fb2326012483d4beac68a97c75e2e734f276`

## Closure status

```text
NOT CLOSED
```

The six planned implementation packages are present and their success-path
contracts are integrated. One failure-reporting gap still violates the Phase 6
boundary audit, so closure would be premature.

## Roadmap verification

| Scope | Implemented evidence | Audit conclusion |
|---|---|---|
| Versioned workflow run | `InvestmentReviewWorkflowRun`, canonical stage order, dependency checks, explicit `COMPLETED`/`SKIPPED`/`FAILED` states | Implemented |
| Typed evidence assembly | `IntegratedInvestmentReviewEvidenceAssembler` with explicit optional-evidence gaps and identity/time validation | Implemented |
| Review generation/export | `IntegratedReviewPackageService` and atomic Review JSON export | Implemented |
| Immutable History | `IntegratedReviewHistoryService` preserves archive/manifest authority separately from SQLite projection | Implemented |
| Historical comparison | `IntegratedReviewComparisonService` selects the previous compatible imported snapshot and distinguishes first-run/unavailable outcomes | Implemented |
| User-facing workflow | `python -m investment_terminal.cli.review` with hermetic first-run and second-run comparison tests | Success path implemented |
| Failure visibility | Required failure and dependent skips persisted in the versioned workflow report, including partial archive success | **Not implemented by the command** |

## Blocking finding

`investment_terminal.cli.review.run()` constructs
`InvestmentReviewWorkflowRun` only after every stage succeeds. Its caller
catches operational exceptions and exits through `argparse.error()` without
writing the configured workflow report.

This creates two observable violations:

1. market refresh or earlier analysis may have completed before a later stage
   fails, but the completed and skipped stage outcomes are not recorded;
2. `HistoricalProjectionAfterArchiveError` carries a successfully registered
   canonical snapshot, but the command does not persist separate completed
   `ARCHIVE_HISTORY`, failed `PROJECT_HISTORY`, and skipped
   `COMPARE_CHANGES` outcomes.

The immutable archive itself remains safe. The defect is workflow reporting,
not History authority or rollback behavior.

## Verified authority boundaries

- application workflow models import no Review or History internals;
- Review generation performs no History, Knowledge, AI, broker, or trade side
  effects;
- canonical archive bytes and append-only manifest remain the historical source
  of truth;
- SQLite remains a rebuildable projection;
- comparison is read-only and uses only compatible imported snapshots;
- the user-facing command does not promote History into Knowledge, invoke a
  grounded-AI provider, access a broker, or execute trades;
- optional Phase 4/5 runtime evidence remains explicitly missing when it has no
  configured source.

## Verification

The focused Phase 6 contract, integration, architecture, and persistence suite
passes: 56 passed.

The complete local regression suite passes: 2680 passed, 4 skipped. The only
warning is the existing Starlette `httpx` deprecation warning.

## Required remediation

Add the smallest command-level failure-reporting coordinator that:

- records the first failed stage and all dependent stages as `SKIPPED`;
- preserves completed earlier-stage artifact identities;
- maps `HistoricalProjectionAfterArchiveError` to completed archive and failed
  projection outcomes using the carried snapshot identity;
- atomically writes the workflow report on both success and operational
  failure;
- returns a non-zero CLI exit after the failed report is durably written;
- adds hermetic failure-path tests without changing analytical, Review, or
  History authority.

After that remediation and a green full suite, repeat this closure audit and
create the final Phase 6 closure record.

## Remediation status

```text
COMPLETE — REPEAT CLOSURE AUDIT REQUIRED
```

The command now constructs the canonical eight-stage report for handled
operational failures, atomically writes it, and then exits non-zero. Hermetic
tests cover validation failure after completed refresh and projection failure
after registered archive success.

Remediation verification passes: 21 focused tests; complete local suite 2681
passed and 4 skipped, with only the existing Starlette `httpx` deprecation
warning.
