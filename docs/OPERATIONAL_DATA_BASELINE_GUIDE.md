# Operational Data Baseline Guide

The command is read-only for every inspected source. `--output` is the only
write and uses atomic replacement.

```powershell
python -m investment_terminal.cli.operational_data_baseline `
  --market-database C:\runtime\market.db `
  --maintained-universe-database C:\runtime\universes.db `
  --current-portfolio C:\runtime\current_portfolio.json `
  --transaction-database C:\runtime\transactions.db `
  --valuation-database C:\runtime\valuations.db `
  --external-context-database C:\runtime\context.db `
  --backup-root C:\runtime\backups `
  --workflow-report C:\runtime\workflow_report.json `
  --output C:\runtime\reports\operational_data_baseline.json `
  --json
```

Every input is optional. Omitted or missing inputs are reported as `ABSENT`.
Provider configuration is inferred only from credential-variable presence;
credential values are never printed or exported.

- `CONFIGURED`: required provider configuration is present;
- `UNCONFIGURED`: it is absent or no concrete adapter exists;
- `READY`: the supplied source passed the read-only structural check;
- `ABSENT`: the source does not exist or was not supplied;
- `ERROR`: the source is malformed, unsupported, or unreadable;
- `UNMEASURED`: no durable evidence was supplied for that measurement.

`READY` does not prove complete or fresh data. Review counts, earliest/latest
timestamps, universe membership, and explicit `UNMEASURED` fields before
selecting the next work. The export may contain local paths and portfolio
name/count metadata and should remain outside public source control.
