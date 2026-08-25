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

Closure readiness is `NOT CLOSED` at baseline `0212fb2`. The success path is
complete, but the command must durably report failed and dependent skipped
stages, including successful archive registration followed by projection
failure. See `docs/PHASE_6_CLOSURE_AUDIT.md`.

The bounded failure-reporting remediation is complete: failed reports preserve
completed artifacts, the first failed stage, dependent skips, and archive
success before projection failure. The next action is the repeated closure
audit.

Phase 6 is closed at verified baseline `2590773`. The closure record is
`docs/PHASE_6_CLOSURE.md`.

Boundary audit:

```text
docs/PHASE_6_WORKFLOW_BOUNDARY_AUDIT.md
```

The workflow coordinates existing public services. It does not own analytical
algorithms, silently promote History into Knowledge, invoke AI implicitly, or
grant trade-execution authority.

---

# Phase 7 — Operational Data and First Real Use

Goal:

Turn the implemented architectural and analytical platform into a populated,
repeatable, operationally verified product using real data.

Scope:

- audit, configure, and connect real market-data providers;
- establish stable bulk and incremental ingestion;
- measure approximately 20-year candle coverage for supported stocks and ETFs;
- establish maintained universes for major companies, approximately the largest
  1000 companies where data and licensing permit, developing/growth companies,
  popular ETFs, and instruments not manually named in advance;
- schedule regular updates and expose refresh status, duration, failures, and
  freshness;
- load and verify the user's real portfolio and transaction history;
- connect real news and external-context sources with provenance, freshness,
  uncertainty, and quality;
- validate screening, discovery, trend, candle-pattern, and recommendation
  evidence on populated datasets;
- prepare a safe portable database or evidence package for explicit ChatGPT
  analysis;
- verify monitoring, backup, restore, recovery, and data-quality reporting;
- run several complete real investment-review workflows and record runtime,
  provider, coverage, quality, and usability gaps before UI design.

Phase 7 must distinguish:

- architecture capability;
- configured provider capability;
- actual populated data coverage;
- measured operational performance;
- analytical evidence;
- AI or human interpretation.

Neither approximately 1000-company universe coverage nor approximately 20-year
candle coverage may be claimed until measured against populated data.

Package 1:

```text
Operational data baseline and coverage report
```

Package 1 is the smallest coherent prerequisite: define one deterministic,
machine-readable operational inventory that reports configured provider
capability, populated candle ranges/counts, maintained-universe membership,
portfolio/context presence, refresh observations, and explicit unknown or
unmeasured states. It must be read-only, use existing repositories and runtime
configuration, and must not add a speculative provider, scheduler, UI, broker,
or analytical authority.

Package 1 is COMPLETE. Its contract, implementation boundary, and verification
record are documented in `docs/PHASE_7_PACKAGE_1.md`.

The first local Package 1 run found no real populated operational inputs and is
recorded in `docs/PHASE_7_OPERATIONAL_BASELINE_1.md`. It selects Package 2 —
Yahoo Historical Candle Operational Qualification — to verify one bounded real
provider request before any bulk ingestion work.

Package 2 implementation is COMPLETE. Its first explicit live request returned
a durably reported `FAILED` result, so operational Yahoo qualification and bulk
ingestion remain incomplete. See `docs/PHASE_7_PACKAGE_2.md`.

The fresh-clone rerun resolved yfinance cache ownership and isolated the
remaining failure to blocked outbound Yahoo HTTPS connectivity. See
`docs/PHASE_7_YAHOO_QUALIFICATION_RERUN.md`.

The repeated local qualification then succeeded for MSFT with 12 daily
candles. Package 3 adds one bounded persistence composition root over the
existing Yahoo client, historical service, and SQLite candle repository.
Broader ingestion remains deferred until its persisted result is reviewed.

Package 3 then succeeded and its exact repeat proved idempotent persistence.
Package 4 adds indexed stored-boundary measurement to report schema version 2;
one controlled one-year MSFT expansion is next, not multi-instrument ingestion.

That expansion stored 251 daily candles across a 364-day observed span.
Package 5 adds History-owned comparison against explicit versioned session
evidence. Calendar sourcing remains the next prerequisite; weekday inference
is prohibited.

Packages 6–8 add the explicit coverage command, integrity validation, and
bounded `XNAS@1` evidence. Package 9 adds separately versioned, official-source
backed `XNAS@2` evidence for the controlled five-year MSFT window. The measured
result is 1,254 expected and observed sessions with no missing or unexpected
candles. Mass ingestion remains out of scope.

Package 10 selects AAPL only after official Nasdaq-listed identity
confirmation, reuses the exact bounded `XNAS@2` evidence, and measures 1,254
observed candles against 1,254 expected sessions with no gaps or unexpected
candles. The exact repeat inserts zero rows. The next boundary is a separate
XNYS instrument/evidence audit; no XNAS calendar may be silently reused.

Package 11 selects `XNYS:IBM` for the later operational run and adds bounded
`XNYS@1` evidence backed only by official ICE/NYSE schedules and the January 9,
2025 exceptional-close memorandum. It emits 1,254 deterministic sessions but
does not ingest IBM. Generating/verifying the JSON and measuring one IBM request
are the next separate operational action.

Package 12 executes and verifies the exact `XNYS@1` document, but the current
permission profile prevents writing it to `C:\runtime\reports` or modifying the
operational SQLite. `IBM_TOTAL=0` was confirmed read-only. IBM ingestion remains
blocked until explicit runtime write access is available; no other instrument
may bypass this step.

Package 13 records a successful user-executed bounded IBM Yahoo qualification:
1,254 daily candles cover the exact requested five-year window and `failure` is
null. Staged `XNYS@1` still passes checksum verification, while read-only
inspection confirms `IBM_TOTAL=0` and SQLite integrity `ok`. The current
execution profile still cannot place the calendar or modify runtime SQLite, so
no ingestion was attempted and no other instrument may bypass this step.

Package 14 completes the controlled IBM/XNYS operational step. The initial
ingestion stores 1,254 daily candles; its exact repeat inserts zero rows and
reports 1,254 duplicates. All 1,254 stored candles match all 1,254 explicit
`XNYS@1` sessions with no missing or unexpected evidence, completeness 1.0,
and SQLite integrity `ok`. A focused measured-state audit is required before
another instrument or broader ingestion is selected.

Package 15 re-runs the read-only operational baseline against the populated
market store. MSFT, AAPL, and IBM each contain 1,254 bounded daily candles, for
3,762 total, while per-series freshness, refresh observability, and measured
performance remain `UNMEASURED`. Existing freshness and refresh services have
no dedicated bounded operational CLI/report. The selected next package is a
single-instrument refresh-observability composition root; scheduling,
multi-instrument refresh, and mass ingestion remain deferred.

Package 16 adds the dedicated single-instrument refresh-observability CLI and
atomic versioned report over the existing Yahoo, repository, freshness, and
refresh boundaries. `SUCCESS`, `NOT_READY`, and `FAILED` outcomes preserve
before/after freshness, exact import evidence, duration, and visible failures.
One explicit live MSFT run is next; no other instrument, scheduler, or mass
refresh is authorized before its result is reviewed.

Package 17 records the first live MSFT refresh report. Trading-session
freshness transitions from `STALE` to `FRESH`; the bounded overlap downloads
10 candles, inserts four, and identifies six duplicates in 1.149708 seconds.
MSFT then contains 1,258 daily candles through 2026-08-24 and SQLite integrity
is `ok`. An exact same-checked-at repeat is required to measure the
already-fresh provider bypass before any broader refresh.

Package 18 confirms that exact same-checked-at repeat: both freshness states
are `FRESH`, refresh is not attempted, import is null, all transfer counters
are zero, and SQLite remains unchanged and healthy. The canonical operational
baseline still cannot consume an explicit refresh report, so its refresh and
performance fields remain `UNMEASURED`. A focused backward-compatibility audit
of that projection is next; another instrument and broader refresh remain
deferred.

Package 19 audits every operational-baseline consumer and selects an optional,
conditional `REFRESH_REPORT` store as the smallest backward-compatible seam.
When no refresh path is supplied, the existing schema-version-1 JSON and its
eight-store inventory must remain unchanged. Explicit valid evidence may make
refresh observability/performance `READY`; malformed, unsupported, or
inconsistent evidence must remain visible and fail closed. This package runs no
refresh and authorizes no broader ingestion.

Package 20 implements that conditional projection without changing baseline
schema version 1 or the omitted-input eight-store shape. Valid `SUCCESS`,
`NOT_READY`, and `FAILED` reports become bounded operational evidence;
malformed, unsupported, inconsistent, naive-time, or invalid-duration reports
remain visible `ERROR` stores and cannot produce measured readiness. A read-only
run against the existing live MSFT report projects nine stores and reports both
refresh observability and measured performance as `READY`. No refresh,
scheduling, multi-instrument aggregation, analysis, or trading is added.

Package 21 repeats the Phase 7 closure-readiness audit against the actual
runtime inventory and the implemented operational boundaries. Phase 7 is not
ready to close: only the market-candle store and one explicit refresh report
are `READY`; current portfolio, transactions, valuations, maintained universe,
external context, backups, and workflow evidence are absent, and broad Phase 7
coverage targets remain unmeasured. The database remains healthy with 3,766
daily candles across MSFT, AAPL, and IBM. The smallest safe next package is a
focused audit of the existing current-portfolio JSON/CSV input, validation,
persistence, privacy, and baseline-projection seams before any private data is
requested or written. Another instrument, scheduler, and mass refresh remain
deferred.

Package 22 audits the complete current-portfolio input surface. The typed JSON
loader, CSV importer, atomic holdings writer, snapshot CLI, repository privacy
guards, and redacted operational-baseline projection already provide the
smallest coherent path; no duplicate qualification code is justified. The
runtime portfolio is absent, the default path is repository-relative, and a
holdings import requires an existing portfolio whose policy and cash balance
remain user-owned. CSV `--preview` exposes full holdings and is not a shareable
operational artifact. Package 23 is therefore a user-executed controlled
runtime qualification: prepare one private portfolio JSON under `C:\runtime`,
validate it locally, and return only the redacted baseline report. Transactions,
valuations, workflow execution, another instrument, scheduling, and mass
refresh remain deferred.

Boundary audit:

```text
docs/PHASE_7_OPERATIONAL_DATA_BOUNDARY_AUDIT.md
```

---

# Phase 8 — User Product Layer

Goal:

Create user-facing application capabilities after real operational gaps have
been measured.

Scope:

- Windows/Desktop UI;
- portfolio dashboard;
- portfolio and transaction editing through the UI;
- provider and refresh configuration;
- explicit manual workflow launch;
- Review Package viewer;
- warnings, freshness, quality, uncertainty, and missing-evidence views;
- History navigation and snapshot comparison;
- reports;
- read-only broker integrations;
- possible Trade Republic integration.

Phase 8 must not move analytical calculations into the UI, hide missing or
low-quality evidence, invoke AI without explicit user action, automatically
promote History into Knowledge, give brokers write access, or execute trades.
