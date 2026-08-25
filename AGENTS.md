# AGENTS.md

## Purpose

This file defines the operating rules for AI-assisted development in InvestmentTerminal.

Before changing code, read:

1. `docs/AI_CONTEXT.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/README.md`
4. `docs/DOMAIN_MAP.md`
5. `docs/ARCHITECTURE_REVIEW_SPRINT_12.md`
6. `docs/AI_ASSISTED_DELIVERY_WORKFLOW.md`
7. relevant domain documentation and tests

## Repository

- Repository: `vactor222123/InvestmentTerminal`
- Default development branch: `develop`
- Primary language: Python
- Test runner: pytest

## Core engineering rules

- Treat the repository as a long-lived product, not a collection of scripts.
- Preserve existing public JSON contracts unless a deliberate versioned migration is approved.
- Keep domain code independent from CLI and presentation layers.
- Keep infrastructure independent from CLI.
- Prefer explicit domain models over loosely shared dictionaries.
- Use timezone-aware datetimes for persisted and exported timestamps.
- UTC is the canonical persistence timezone.
- Preserve immutable historical evidence.
- Keep the historical manifest append-only.
- Treat SQLite history as rebuildable query storage, not canonical evidence.
- Keep behavior deterministic and explicitly ordered.
- Do not introduce circular dependencies.
- Do not perform broad rewrites when a focused change is sufficient.
- Do not add abstractions before repeated use is demonstrated.
- Reuse existing helpers and conventions before creating new ones.
- Any new helper under `investment_terminal/utils` must:
  - be domain-independent;
  - solve a repeated cross-domain problem;
  - have focused tests.

## Persistence rules

- Mutable JSON documents must use atomic write helpers.
- Immutable historical archives must preserve exact source bytes.
- Exclusive archive creation must remain exclusive.
- Append-only manifests must not be silently rewritten as mutable documents.
- Multi-table imports must have explicit transaction ownership and rollback behavior.
- No persistence failure may silently produce partial success.

## Validation rules

Use shared validation helpers for stable cross-domain primitives:

- required and optional text;
- timezone-aware datetimes;
- finite numbers;
- bounded scores.

Keep domain-specific validation inside the owning domain model.

## Testing rules

For each logical change:

1. run focused tests;
2. run the full test suite;
3. keep all existing tests green;
4. add failure-path tests when persistence or external data is involved.

Do not change tests merely to hide a regression.

## Change discipline

- One logical change per commit.
- Prefer small, reviewable packages.
- Preserve backward compatibility unless the task explicitly approves a breaking change.
- Update documentation when architecture, contracts, workflows, or status change.
- Record major architectural decisions in ADRs.
- Do not invent missing facts from absent data.
- Do not silently normalize away errors that should remain visible.

## Package delivery discipline

- Start every package from a fresh `develop` clone at the exact caller-supplied
  GitHub SHA; stop on a baseline, branch, or clean-worktree mismatch.
- Classify the package as `AUDIT`, `IMPLEMENTATION`, or `OPERATIONAL` and keep
  it to one smallest coherent change and one conventional local commit.
- For user-executed runtime work, provide one bounded PowerShell block and mark
  explicit `SEND` and `DO NOT SEND` paths.
- Treat `C:\runtime\data` as private by default. Review only explicitly returned
  redacted operational reports; never include runtime inputs in Git or ZIP.
- Use unique repository-local pytest `--basetemp` paths when the system temp
  root is inaccessible, and exclude them from commits and ZIP artifacts.
- Package complete changed files at repository-relative paths, verify ZIP
  contents, and report the final SHA-256.
- Keep `PROJECT_CONTINUATION.md` concise; preserve detailed historical package
  evidence in its owning `docs/PHASE_*` record and Git history.

The complete handoff protocol is `docs/AI_ASSISTED_DELIVERY_WORKFLOW.md`.

## Expected workflow

1. Audit the relevant subsystem.
2. Read the existing implementation and tests.
3. Design the smallest coherent change.
4. Implement code and focused tests.
5. Run focused tests.
6. Run the full suite.
7. Update documentation if needed.
8. Commit with a conventional message.
