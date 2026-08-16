# Post-Sprint-32 Audit

Baseline: `develop @ 68690fc`

## Finding

The highest-value remaining bottleneck is current-state market-intelligence composition.

InvestmentTerminal already has a real live equity-analysis pipeline:

```text
Yahoo OHLCV refresh
→ freshness enforcement
→ technical analysis
→ Yahoo fundamentals
→ sector-aware fundamental scoring
→ asset analysis
→ ranking
→ coverage-aware recommendations
→ investment theses
→ target allocation
→ JSON export
```

Canonical existing CLI:

```text
python -m investment_terminal.cli.portfolio_ranking
```

The main gap is that the unified Review Package still consumes a previously
exported stock-analysis JSON file instead of composing the live typed analysis
directly. ETF analysis and watchlist analysis remain `NOT_CONNECTED`; news and
geopolitical context are explicitly external.

Therefore the Terminal can already analyze a live stock universe, but it does
not yet provide one canonical integrated "analyze the market now" workflow.

## Practical command today

Windows PowerShell:

```powershell
python -m investment_terminal.cli.portfolio_ranking `
  --universe us_large_cap_30 `
  --capital 100000 `
  --profile BALANCED `
  --resolution D
```

## Authority constraint

Preserve:

```text
external/current data
→ deterministic analysis
→ Review Package
→ History
→ explicit History-to-Knowledge ingestion
→ Knowledge
→ grounded AI
```

Do not bypass this by feeding arbitrary live provider text directly into AI.

## Approved direction

```text
Sprint 33 — Integrated Current-State Market Intelligence
```

Goal:

```text
one canonical live analysis workflow
→ deterministic stock analysis
→ integrated Review Package
→ optional explicit History handoff
```

Deferred pending separate audits:

```text
ETF-specific intelligence
watchlist intelligence
news/geopolitical ingestion
macro provider integration
distributed/multi-instance state
broker execution
autonomous portfolio actions
```
