# InvestmentTerminal — Roadmap After Audit

## Purpose

This document defines the development order after the complete product alignment audit.

Source documents:

- docs/PROJECT_VISION.md
- docs/PROJECT_FULL_AUDIT.md

The roadmap follows the existing architecture:

Data
→ Deterministic Analysis
→ Review Package
→ History
→ Knowledge
→ AI Interpretation

---

# Phase 1 — Multi-Asset Evidence Foundation

Goal:

Expand from stock-focused analysis into a broader investment data platform.

Scope:

- ETF data contracts
- fund/security identity model
- exchange metadata
- currency support
- trading calendars
- source provenance
- data quality contracts

Outcome:

A reliable foundation for stocks, ETFs and additional asset classes.

---

# Phase 2 — Portfolio Lifecycle Intelligence

Goal:

Transform portfolio snapshots into a complete investment history.

Scope:

- transaction ledger
- purchases/sales
- dividends
- fees
- realised/unrealised performance
- portfolio valuation history
- tax-lot readiness

Outcome:

Full portfolio evolution analysis.

---

# Phase 3 — Portfolio Decision Intelligence

Goal:

Improve investment decisions.

Scope:

- portfolio risk analysis
- drawdown analysis
- volatility
- correlation
- rebalancing evidence
- strategy-specific rules:
  - CORE_LONG_TERM
  - STOCK_LONG_TERM
  - POSITION_TRADE
  - CASH_RESERVE

Outcome:

Evidence-based portfolio improvement recommendations.

---

# Phase 4 — Context and Market Intelligence

Goal:

Add information that cannot be represented only by financial metrics.

Scope:

- news ingestion
- macroeconomic data
- geopolitical context
- events
- sentiment/context evidence

Requirements:

- provenance
- freshness
- explicit uncertainty

Outcome:

Richer AI-assisted investment reviews.

---

# Phase 5 — Market Discovery

Goal:

Analyze the broader investment universe.

Scope:

- maintained asset universe
- thousands of companies
- ETF discovery
- sector analysis
- screening pipeline

Outcome:

Find opportunities beyond manually configured assets.

---

# Phase 6 — Integrated Investment Review Workflow

Goal:

Create the complete operating workflow.

Future workflow:

refresh data
→ validate evidence
→ analyze portfolio
→ analyze market
→ generate Review Package
→ archive history
→ compare changes
→ produce investment review

Audited implementation order:

1. immutable workflow run and stage-result contract — COMPLETE;
2. typed deterministic evidence assembly across portfolio, context, and market
   discovery boundaries — COMPLETE;
3. Review Package generation and atomic export — COMPLETE;
4. explicit immutable archive and rebuildable History projection stages —
   COMPLETE;
5. deterministic previous-snapshot selection and comparison — COMPLETE;
6. one user-facing review command with a hermetic end-to-end contract —
   COMPLETE.

Boundary audit:

```text
docs/PHASE_6_WORKFLOW_BOUNDARY_AUDIT.md
```

The workflow coordinates existing public services. It does not own analytical
algorithms, silently promote History into Knowledge, invoke AI implicitly, or
grant trade-execution authority.

---

# Phase 7 — User Product Layer

Goal:

Create user-facing application capabilities.

Scope:

- Windows/Desktop UI
- portfolio dashboard
- review navigation
- reports
- read-only broker integrations
- Trade Republic integration possibility

Automatic trade execution remains outside scope.
