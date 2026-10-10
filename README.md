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

`python -B -m investment_terminal.cli.portfolio_split_diagnose --help` describes
one checksum-bound diagnostic replay of a failed action request. It retains new
evidence without resuming the batch or changing holdings; send only its redacted
report. See [provider diagnostic](docs/PHASE_7_SPLIT_PROVIDER_DIAGNOSTIC.md).

For collection startup diagnosis, add `--preflight-only` to
`python -B -m investment_terminal.cli.portfolio_split_collect` with the usual
arguments. It prints a safe diagnosis without provider requests or runtime writes;
send only `PREFLIGHT_RESULT` and the exit code. It does not prove live readiness.

`python -m investment_terminal.cli.portfolio_split_collect --help` describes
bounded action collection with automatic canonical-CSV discovery, private
snapshot reuse and a redacted report. It collects candidate events, not adjusted
broker holdings. See [portfolio split collection](docs/PHASE_7_PORTFOLIO_SPLIT_COLLECTION.md).

Split handling now has an explicit, non-destructive projection core and an
offline position command (`python -m investment_terminal.cli.split_positions
--help`). It uses original broker trades and existing pinned action snapshots;
it does not rewrite stored Yahoo prices or change legacy portfolio valuation.
Operational qualification and known source-price basis remain required before
production integration. See [split adjustment](docs/PHASE_7_SPLIT_ADJUSTMENT.md).

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

One-command corporate actions plus verified research export:

```text
python -m investment_terminal.cli.instrument_research_collect --help
```

Supply the existing weekly profile, pinned projection, selected symbol/window,
new run ID and action-age policy. The command derives output paths, collects
actions (or explicitly reuses a pinned snapshot offline), exports schema 2,
verifies the persisted pair and checks SQLite integrity. Existing files are not
overwritten and stored candles are not updated. See
`docs/PHASE_7_CORPORATE_ACTION_RESEARCH_RUN.md` for failure/recovery and privacy.

Yahoo normalized dividends, splits and available capital-gain observations:

```text
python -m investment_terminal.cli.yahoo_corporate_actions --help
```

It collects one explicit bounded symbol/window into a private validated snapshot
and a separate redacted report. Existing matching snapshots are reused offline;
new snapshot paths request a fresh full window without rewriting older evidence.
No manual action entry, candle rewrite or portfolio transaction is involved.
It does not establish cash-action currency or calculate total return. See
`docs/PHASE_7_YAHOO_CORPORATE_ACTION_COLLECTION.md`.

Paused experiment: public EODHD one-ETF demo price-shape qualification:

```text
python -m investment_terminal.cli.eodhd_demo_price_qualification
```

It uses only `VTI.US` and the public `demo` token, makes one read-only bounded
request, and writes a redacted aggregate report rather than prices or candles.
It does not qualify corporate actions or authorize bulk acquisition; see
`docs/PHASE_7_EODHD_PUBLIC_DEMO_PRICE_QUALIFICATION.md`.

Local selected-instrument research handoff verification:

```text
python -m investment_terminal.cli.instrument_research_verify
```

It verifies an existing private export against an exact-byte-pinned redacted
report and a caller-selected symbol, without writing or uploading data. See
`docs/PHASE_7_INSTRUMENT_RESEARCH_VERIFIER.md`.

Profile-backed selected-instrument research export:

```text
python -m investment_terminal.cli.instrument_research_run
```

It reuses the private weekly profile and the existing read-only export,
reducing manually repeated evidence paths without changing export contracts.
The selected symbol, explicit window, projection SHA-256, and private/redacted
destinations remain caller-owned. See
`docs/PHASE_7_PROFILE_BACKED_RESEARCH_RUN.md`.

Both research export commands now offer explicit `--schema-version 2` to add
corporate-action context. Supply `--actions-as-of` and
`--actions-maximum-age-days`; optionally supply a matching `--actions-snapshot`
and `--actions-sha256`. Missing/stale evidence is labeled, not filled with zeros.
The local verifier accepts both versions. Default schema 1 and raw-price/SMA
semantics are unchanged. See `docs/PHASE_7_RESEARCH_CORPORATE_ACTION_CONTEXT.md`.

Read-only single-instrument research export:

```text
python -m investment_terminal.cli.instrument_research_export
```

It validates a private full raw-indicator projection against the selected
manifest and weekly checkpoint, exports one bounded private candle/indicator
artifact, and writes a separate redacted report. It does not share values
with ChatGPT or update SQLite; see
`docs/PHASE_7_INSTRUMENT_RESEARCH_EXPORT.md`.

Bounded profile-backed weekly candle slice:

```text
python -m investment_terminal.cli.weekly_run
```

It requires a verified private runtime profile, explicit exclusive UTC end,
item budget, and slice ID. It is not a scheduler or a data-quality verdict;
see `docs/PHASE_7_WEEKLY_RUN_CLI.md`.

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

One manifest-bound batch execution:
`python -m investment_terminal.cli.manifest_bound_market_batch`. It validates
the private manifest, selected index, and request checksum before executing only
that request through the existing resumable ingestion boundary.

Evidence-bound partial timeout retry:
`python -m investment_terminal.cli.manifest_partial_timeout_retry`. It verifies
an immutable redacted causal inventory against the current private checkpoint,
retries only the unique stored timeout once, and atomically preserves the new
outcome without processing unrelated failures or missing members.

Completed-sweep failure inventory:
`python -m investment_terminal.cli.manifest_collection_failure_inventory`. It
verifies the checksum-bound completed sweep and all private request checkpoints,
then writes only aggregate retryable-causal and terminal-policy evidence.

Completed-sweep no-price transition:
`python -m investment_terminal.cli.manifest_completed_sweep_no_price_transition`.
It operates offline, verifies immutable inventory and complete checkpoint parity
before writing, atomically finalizes only recognized stored no-price outcomes
under a bounded checkpoint budget, and emits a redacted resumable report.

Bounded manifest drain:
`python -m investment_terminal.cli.manifest_batch_drain`. It resumes from
validated private per-batch checkpoints and processes at most 100 explicitly
authorized first-unfinished requests, stopping on the first non-success result.

Broad US universe qualification:
`python -m investment_terminal.cli.nasdaq_universe_qualification`. It archives
two official Nasdaq Trader directories and emits private normalized evidence
plus a separate redacted aggregate report.
