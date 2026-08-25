# AI-Assisted Delivery Workflow

## Purpose

This document defines the repeatable delivery protocol for small AI-assisted
InvestmentTerminal packages. It optimizes handoff and operational evidence
transfer without weakening architecture, privacy, testing, or Git controls.

## Package Start Contract

Every package starts from a fresh clone of `develop`. The caller supplies the
exact GitHub baseline SHA, normally as:

```text
<full SHA> далі
```

Before reading or changing package files, verify:

```text
git rev-parse HEAD == supplied baseline SHA
git branch --show-current == develop
git status --short is empty
```

A mismatch stops the package. Never infer or substitute a nearby baseline.

## Package Types

Every package has one primary type:

- `AUDIT`: read-only subsystem inspection plus documentation; no operational
  mutation and no implementation without a separately justified package;
- `IMPLEMENTATION`: one bounded code/contract change with focused and
  failure-path tests;
- `OPERATIONAL`: one explicit user-executed runtime action followed by review
  of a redacted durable report.

A package must remain the smallest coherent unit and produce exactly one
conventional local commit. Package type does not relax full-suite or whitespace
verification.

## Operational Handoff Contract

The AI execution profile may not be able to write `C:\runtime`. When user
execution is required, provide one complete PowerShell block that:

1. uses explicit absolute runtime paths;
2. creates only the required directories;
3. runs the bounded command;
4. validates the generated JSON where applicable;
5. prints the report path and SHA-256 where useful.

Every operational handoff must end with explicit labels:

```text
SEND: redacted report path(s)
DO NOT SEND: private source/database/preview path(s)
```

Runtime ownership is separated as follows:

```text
C:\runtime\data\     private databases, portfolio and transaction inputs
C:\runtime\reports\ redacted operational evidence eligible for review
```

A report is not shareable merely because it is under `reports`; inspect its
contract first. Raw portfolio JSON, transaction CSV, database files, secrets,
and previews containing holdings or costs remain private unless the user
explicitly changes that boundary.

## Test Execution Contract

Run one domain-scoped focused selection, then one complete suite. On restricted
Windows profiles, use unique repository-local pytest temporary roots:

```powershell
python -m pytest --basetemp=.pytest-<package>-focused <focused tests>
python -m pytest --basetemp=.pytest-<package>-full
git diff --check
```

Temporary test roots must never be committed or included in the package ZIP.
An environment-only failure may be rerun with a corrected local `--basetemp`,
but both the initial failure and successful rerun must be reported accurately.

## Documentation and Handoff Discipline

`PROJECT_CONTINUATION.md` remains the canonical execution checkpoint, not the
complete historical archive. Keep the current package and only the context
needed to resume safely; older detail belongs in immutable `docs/PHASE_*`
records and Git history. Do not duplicate long historical package narratives
when a precise link and concise result are sufficient.

The final handoff must contain:

- concise audit/result;
- focused and full test results;
- `git diff --check` result;
- local commit SHA;
- ZIP link and SHA-256;
- exact `git add`, `git commit`, and `git push` commands;
- one exact next operational step.

## ZIP Contract

The ZIP contains complete changed files at their repository-relative paths.
It must exclude `.git`, pytest temporary roots, caches, secrets, runtime data,
private inputs, databases, and unrelated user files. Verify the ZIP entry list
before delivery and calculate SHA-256 from the final bytes.

## Candidate Automation

A future bounded tooling package may add
`scripts/build_change_package.ps1` to derive the committed changed-file list,
enforce exclusions, run the whitespace gate, build the structured ZIP, verify
entries, calculate SHA-256, and print exact Git commands. It requires a focused
audit and failure-path tests before implementation; this workflow document does
not authorize an untested packaging script.
