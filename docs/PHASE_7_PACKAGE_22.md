# Phase 7 Package 22 — Current-Portfolio Operational Input Audit

Source baseline: `develop @ 944dad2d048ecdef21b9727408b767e231d93841`.

## Decision

The current repository already contains the smallest coherent implementation
for controlled current-portfolio qualification. No new loader, writer, report,
or JSON contract is justified by the measured state.

## Verified Boundaries

`CurrentPortfolioLoader` validates one JSON object containing the portfolio
name, policy, cash balance, and holdings. Domain models validate supported
asset types, sleeves and strategies, canonical instrument identity, unique
instruments, finite positive quantities, non-negative costs/cash/contributions,
and policy weights.

`PortfolioHoldingCsvImporter` validates the canonical CSV schema and reports
line-specific failures. `CurrentPortfolioWriter` loads the existing portfolio,
replaces only holdings, preserves user-owned name, policy, and cash, and writes
atomically. Therefore holdings CSV cannot bootstrap a portfolio by itself; an
explicit user-owned JSON source must exist first.

The default loader path is repository-relative:

```text
data/portfolios/current_portfolio.json
```

The canonical repository-local personal JSON, holdings CSV, and quote JSON are
ignored by Git and enforced by tests. The operational runtime currently has no
`C:\runtime\data\current_portfolio.json` and no current-portfolio baseline
report.

## Privacy Finding

The holdings-import `--preview` output includes complete holding identities,
quantities, average costs, and derived totals. It is useful for private local
validation but is not a redacted or shareable operational artifact.

The existing operational baseline is the correct handoff boundary. With an
explicit `--current-portfolio` path it loads the typed portfolio and projects
only:

```text
configured path
READY | ABSENT | ERROR
portfolio name
holding count
base currency
```

It does not serialize holdings, quantities, average costs, cash, monthly
contribution, policy weights, or source file contents. A run against the tracked
example produced `CURRENT_PORTFOLIO=READY`, two holdings, and `EUR` without
exposing private position data.

## Selected Operational Handoff

```text
Phase 7 Package 23 — Controlled Current-Portfolio Runtime Qualification
```

The user should create and edit one private runtime JSON from the tracked
example, validate it locally, and generate a redacted operational baseline that
also references the existing market database and MSFT refresh report. Only that
baseline report should be returned for review; the private JSON and CSV preview
must remain local.

This audit does not authorize committing personal data, transaction import,
valuation generation, workflow execution, another instrument, scheduling,
mass refresh, AI invocation, broker access, or trading.

## Verification

```text
repository privacy audit: all canonical personal files IGNORED; examples PRESENT
focused portfolio/privacy/baseline/architecture: 72 passed
full: 2,743 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
