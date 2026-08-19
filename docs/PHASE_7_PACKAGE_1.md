# Phase 7 Package 1 — Operational Data Baseline and Coverage Report

## Verified baseline

`develop @ b7094a3123694596bee2ec046ca0ff7bea9f114a`

## Status

```text
COMPLETE
```

## Delivered boundary

Package 1 adds a versioned immutable operational report, a deterministic
read-only inspection service, and a CLI composition root:

```text
python -m investment_terminal.cli.operational_data_baseline
```

The report covers provider configuration state, candle ranges/counts,
maintained-universe snapshots and asset types, current portfolio presence,
transaction and valuation ranges, external-context ranges, runtime backup
metadata, and one explicit workflow report when supplied.

All SQLite inspection uses URI `mode=ro`. Missing paths remain `ABSENT` and are
not created. Unsupported schemas and malformed sources remain visible as
`ERROR`. Provider credential values are never projected. Refresh observability
and measured performance remain `UNMEASURED` unless a durable workflow report
is explicitly supplied.

## Authority boundary

The report distinguishes configured capability from populated coverage and
measured runtime evidence. It does not calculate analysis, interpret evidence,
invoke AI, promote History into Knowledge, access a broker, or execute trades.

No approximately 20-year candle or approximately 1000-company coverage claim is
made. The report supplies the evidence required to measure those targets later.

## Verification contract

Focused tests cover empty sources, secret redaction, deterministic coverage,
no creation of absent databases, malformed or unsupported stores, invalid
portfolio input without content leakage, timezone validation, workflow-derived
observability, JSON output, and atomic export.

## Next operational action

Run the report against explicit real local paths and provider configuration,
preserve the output outside source control, and use its measured gaps to select
Phase 7 Package 2. Do not add a provider or bulk ingestion package before that
real baseline is reviewed.
