# Investment Terminal

> Professional private investment intelligence system

## Overview

Investment Terminal is a modular Python application for deterministic investment
analysis, immutable historical evidence, explicit Knowledge construction,
evidence-grounded AI, controlled production delivery, and reproducible software
execution.

The system prioritizes:

- correctness;
- determinism;
- traceability;
- historical integrity;
- explicit authority boundaries;
- explicit human decision ownership;
- reproducible delivery.

## Continuing Development

The durable execution/handoff checkpoint is:

```text
PROJECT_CONTINUATION.md
```

Read it before resuming implementation in a new development or ChatGPT session.
It records the verified baseline, current audit-driven development phase,
approved Sprint plan, exact next Task, failure lessons, and working protocol.

It MUST be updated after every completed Task.

## Authority Hierarchy

```text
Current-state deterministic analysis
→ Review Package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ grounded generation
→ grounding validation
→ ADMISSIBLE generated evidence
→ durable grounded-generation persistence
```

Persisted grounded generations remain downstream generated evidence. They are
not automatically promoted into History or Knowledge.

Provider usage/cost accounting remains a parallel operational boundary.

## Core Capabilities

### Current-state intelligence

- market-data acquisition and validation;
- technical/fundamental analysis;
- ranking and machine recommendations;
- portfolio policy, holdings, snapshots, and contribution planning;
- versioned Review Package generation.

### Historical intelligence

- immutable exact-byte Review Package archive;
- SHA-256 verification;
- append-only manifest;
- rebuildable SQLite historical projection;
- comparison, timeline, and replay;
- methodology-aware outcome research.

### Knowledge

- immutable/versioned records;
- exact evidence references;
- deterministic SQLite persistence;
- explicit verified History-to-Knowledge ingestion;
- dry-run and idempotent ingestion semantics.

### Evidence-grounded AI

- provider-neutral prompt/result protocols;
- deterministic Knowledge selection;
- strict response parsing and citation validation;
- ADMISSIBLE/REJECTED grounding validation;
- provider governance, pricing, and budgets;
- deeply immutable persisted ADMISSIBLE generations;
- strict JSON persistence;
- bounded history queries;
- read-only CLI and authenticated HTTP inspection.

### Production runtime

Canonical factory:

```text
investment_terminal.server.production:create_app
```

Canonical server CLI:

```text
python -m investment_terminal.cli.server
```

Routes:

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations?limit=<N>
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

## Reproducible Development

Supported lock-generation family:

```text
Python 3.13.x
```

Dependency source manifests:

```text
requirements.in
requirements-dev.in
```

Generated hash locks:

```text
requirements.lock
requirements-dev.lock
```

Compile locks on Windows PowerShell:

```powershell
.\scripts\compile_requirements.ps1
```

Install the development/test environment:

```powershell
python -m pip install --require-hashes -r requirements-dev.lock
```

Do not use `pip freeze` as the project dependency source of truth.

## Continuous Integration

Canonical workflow:

```text
.github/workflows/ci.yml
```

CI runs on pushes to `develop` and pull requests targeting `develop`.

Quality gate:

```text
locked install
→ dependency reproducibility contract
→ architecture dependency guards
→ full pytest
→ git diff --check
```

The regression suite is designed to run from a clean checkout and must not
depend on developer-local personal portfolio files.

## Operational CLIs

Integrated investment review:

```text
python -m investment_terminal.cli.review
```

The command refreshes and analyzes the configured market universe, assembles
the current portfolio and explicit optional-evidence gaps, exports one Review
Package, preserves and projects History, compares the previous compatible
imported snapshot, and writes a versioned workflow report. It does not invoke
AI, promote History into Knowledge, or execute trades.

History:

```text
python -m investment_terminal.cli.import_history
python -m investment_terminal.cli.query_history
python -m investment_terminal.cli.compare_history
python -m investment_terminal.cli.replay_history
```

Knowledge:

```text
python -m investment_terminal.cli.knowledge
python -m investment_terminal.cli.ingest_history_knowledge
```

Provider accounting:

```text
python -m investment_terminal.cli.provider_usage_cost
```

Generated evidence:

```text
python -m investment_terminal.cli.grounded_generations
```

Parse-only transaction CSV qualification:

```text
python -m investment_terminal.cli.transaction_csv_qualification
```

Its redacted atomic report contains aggregate qualification evidence only and
does not persist transactions.

Bounded durable transaction import:

```text
python -m investment_terminal.cli.transaction_csv_import
```

The command uses explicit immutable ledger metadata, atomic batch persistence,
and an atomic redacted aggregate report. It does not generate valuations,
execute the integrated workflow, invoke AI, or authorize trading.

## Historical Source-of-Truth Rule

```text
Archived Review Package JSON
    canonical historical evidence

manifest.jsonl
    append-only navigation index

history.db
    rebuildable structured projection
```

Archived historical evidence must not be rewritten.

## Project Philosophy

**Data Quality First. Evidence Before Narrative. History Is Immutable.
Authority Must Be Explicit. Delivery Must Be Reproducible.**

Investment Terminal is research and decision-support software. It does not
execute trades and does not transfer final investment authority away from the
user.
The bounded transaction-derived valuation CLI is
`python -m investment_terminal.cli.transaction_derived_valuation`. Its quote
JSON, transaction database, and valuation database are private runtime inputs;
only the redacted operational report is shareable after inspection.
Read-only quote qualification: `python -m investment_terminal.cli.offline_quote_qualification`.
It optionally accepts `--instrument-metadata` together with
`--metadata-maximum-age-days` to enrich transaction-derived positions from
explicit private provenance-bearing evidence without changing the ledger.
Automated metadata bootstrap: `python -m investment_terminal.cli.openfigi_metadata_bootstrap`.
It uses OpenFIGI v3, preserves raw responses privately, and emits only a
redacted aggregate report with privacy-safe failure categories;
`OPENFIGI_API_KEY` is optional. The required `--private-diagnostic-output`
points to a local-only JSON file written only when the candidate ticker is
absent; that file must not be shared.
Automated ISIN discovery qualification:
`python -m investment_terminal.cli.yahoo_isin_search_qualification`. It reads
the private OpenFIGI diagnostic, queries Yahoo without manual ticker input,
writes private normalized candidates, and emits a separate redacted report.
Exact ticker-match qualification:
`python -m investment_terminal.cli.yahoo_ticker_match_qualification`. It reads
private diagnostic, Yahoo-candidate, and quote documents and accepts only one
exact existing-ticker match without mutating runtime data.

Phase 7 operational MVP direction: the user supplies private portfolio
transactions; InvestmentTerminal automatically maintains ten-year market data,
deterministic indicators, and portfolio-performance evidence. Final investment
interpretation belongs to the user or a separate ChatGPT analysis.

Bounded resumable bootstrap:
`python -m investment_terminal.cli.resumable_market_batch`. It accepts a
private versioned request/checkpoint and emits a redacted aggregate report.

Offline deterministic batch planning:
`python -m investment_terminal.cli.market_batch_manifest`. It joins the private
eligibility-success projection with complete currency evidence, writes a
private versioned manifest of bounded requests, and emits a separate redacted
aggregate report without contacting Yahoo or ingesting candles.

Broad US universe qualification:
`python -m investment_terminal.cli.nasdaq_universe_qualification`. It archives
two official Nasdaq Trader directories and emits private normalized evidence
plus a separate redacted aggregate report.
