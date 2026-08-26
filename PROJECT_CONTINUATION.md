# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint

**Current repository:** `vactor222123/InvestmentTerminal`
**Current branch:** `develop`
**Current GitHub baseline:** `069a8fd43a60fc77d63a4c26961ba93677baab23`
**Current local package:** Phase 7 Package 48 - Local-Only Candidate-Absence Diagnostic Audit
**Current phase:** Phase 7 — Operational Data and First Real Use — OPEN
**Current next action:** Implement the local-only candidate-absence diagnostic

---

## Current State

Sprint 33 — Integrated Current-State Market Intelligence:

```text
CLOSED
```

A complete product alignment audit has been performed.

Phase 1 Package 1 establishes a provider-independent immutable instrument
identity contract and makes current portfolio holdings expose that contract
without changing their existing serialized JSON shape.

Phase 1 Package 2 adds explicit exchange, trading-calendar, and currency
metadata contracts and supports exchange-scoped ticker identity without
changing existing portfolio serialization.

Phase 1 Package 3 adds traceable market-metadata source provenance and
deterministic READY/PARTIAL/STALE quality assessment.

Phase 1 Package 4 adds provider-independent ETF characteristics and an
evidence envelope that preserves missing facts, source provenance, and quality.

Phase 1 Package 5 adds constituent-holding and categorical-exposure contracts
with explicit partial coverage, provenance, and quality.

Phase 1 is closed after verifying its complete roadmap scope and green CI.
Phase 2 Package 1 establishes immutable portfolio lifecycle transaction and
deterministically ordered ledger contracts without changing current snapshots.

Phase 2 Package 2 establishes append-only repository semantics and an in-memory
reference implementation with deterministic time and instrument queries.

Phase 2 Package 3 adds a versioned SQLite store and durable repository adapter
with immutable ledger metadata, strict JSON payloads, and rollback behavior.

Phase 2 Package 4 adds provider-neutral import batches and deterministic,
visible accounting for imported and duplicate transaction identities.

Phase 2 Package 5 adds a canonical provider-neutral transaction CSV schema,
line-specific validation, and lossless conversion into transaction import batches.

Phase 2 Package 6 adds deterministic open-position reconstruction from BUY and
SELL events with average-cost accounting and fail-closed oversell validation.

Phase 2 Package 7 adds deterministic realised gain/loss calculation per SELL
event and currency-safe summaries using the established average-cost method.

Phase 2 Package 8 adds quote-backed unrealised performance for reconstructed
positions with explicit valuation time, quote provenance, and currency isolation.

Phase 2 Package 9 adds immutable transaction-derived valuation snapshots and a
deterministically ordered portfolio valuation history contract.

Phase 2 Package 10 adds append-only valuation repository semantics and an
in-memory reference implementation with deterministic temporal queries.

Phase 2 Package 11 adds versioned SQLite valuation-history persistence with
immutable ownership metadata, strict JSON payloads, indexed temporal queries,
transaction rollback, and lossless restart reconstruction.

Phase 2 Package 12 adds explicit acquisition-lot selection and deterministic
lot-level attribution without imposing an implicit jurisdictional disposal method.

Phase 2 is closed after verifying every roadmap scope item against the current
Portfolio modules and tests at green CI baseline `349620e`. The closure record
is `docs/PHASE_2_CLOSURE.md`.

Phase 3 Package 1 adds provider-neutral, currency-explicit portfolio and
instrument return-series inputs with ordered periods, cutoff validation, and
source provenance, without calculating or classifying risk.

Phase 3 Package 2 adds compounded portfolio drawdown analysis with an explicit
wealth path, running peaks, maximum peak-to-trough evidence, and recovery state.

Phase 3 Package 3 adds sample portfolio volatility and explicit annualisation
without hidden cadence or market-calendar assumptions.

Phase 3 Package 4 adds pairwise Pearson correlation evidence with exact period
alignment and explicit unavailable states for incompatible or insufficient data.

Phase 3 Package 5 converts canonical policy gaps into non-executable strategic
bucket adjustment evidence with an explicit caller-supplied tolerance.

Phase 3 Package 6 adds a complete versioned rule contract with separate review
cadence and measurable conditions for every canonical portfolio strategy.

Phase 3 Package 7 deterministically evaluates explicit metric evidence against
the effective strategy rule set with traceable PASS/FAIL/REVIEW outcomes.

Phase 3 is closed after verifying every roadmap scope item and green CI through
run 66. The closure record is `docs/PHASE_3_CLOSURE.md`.

Phase 4 Package 1 establishes provider-independent immutable external-context
records for news, macroeconomic, geopolitical, and event evidence with explicit
source provenance, caller-configured freshness, quality status, and uncertainty.

Phase 4 Package 2 adds a provider-neutral bounded query and ingestion boundary
that validates normalized provider output, rejects scope and identity defects,
applies freshness quality, and returns deterministic evidence without storage.

Phase 4 Package 3 adds append-only external-context repository semantics and an
in-memory reference implementation with deterministic time and subject queries.

Phase 4 Package 4 adds versioned SQLite persistence and a durable append-only
repository adapter for external-context evidence.

Phase 4 Package 5 adds deterministic external-context projection into the
Review Package while preserving provenance, freshness, quality, and uncertainty.

Phase 4 Package 6 adds provider-independent sentiment evidence and lossless
Review Package association with explicit missing-assessment accounting.

Phase 4 is closed after verifying every roadmap scope item against the current
Context, Review, persistence, and test boundaries. The closure record is
`docs/PHASE_4_CLOSURE.md`.

Phase 5 Package 1 establishes immutable, versioned maintained asset-universe
snapshots using canonical instrument identities, effective membership time,
source provenance, and explicit quality without changing the legacy symbol-list
universe contract.

Phase 5 Package 2 adds a provider-neutral bounded query and ingestion boundary
that validates normalized provider snapshots, rejects scope and identity
defects, applies freshness quality, and returns deterministic universe evidence
without persistence or screening.

Phase 5 Package 3 adds append-only maintained-universe repository semantics and
an in-memory reference implementation with deterministic temporal, universe,
and canonical instrument membership queries.

Phase 5 Package 4 adds versioned SQLite persistence and a durable append-only
repository adapter for maintained-universe evidence with indexed queries,
strict JSON reconstruction, rollback, and restart safety.

Phase 5 Package 5 adds deterministic ETF discovery assembly from maintained
universe membership and existing ETF characteristics/composition contracts with
explicit missing evidence and quality, without scoring or recommendation.

Phase 5 Package 6 adds descriptive sector and industry evidence for classified
STOCK members with explicit coverage and unclassified identity accounting.

Phase 5 Package 7 adds a deterministic, versioned screening boundary with
caller-owned thresholds, explicit missing-data handling, traceable metric
evidence, and no ranking or recommendation authority.

Phase 5 is closed after verifying every roadmap scope item against the current
Universe models, ingestion, repositories, discovery/analysis builders,
screening pipeline, and green full suite. The closure record is
`docs/PHASE_5_CLOSURE.md`.

The Phase 6 workflow boundary audit verifies that refresh, deterministic
analysis, Review generation, immutable archival, History projection, comparison,
Knowledge, and grounded-AI capabilities already exist behind separate public
boundaries. The missing capability is a thin application-level run contract and
coordinator with explicit stage outcomes and fail-closed dependencies. The audit
record is `docs/PHASE_6_WORKFLOW_BOUNDARY_AUDIT.md`.

Phase 6 Package 1 establishes an immutable, versioned application contract for
the complete workflow attempt. Eight canonically ordered stage results preserve
explicit dependencies, `COMPLETED`/`SKIPPED`/`FAILED` outcomes, timezone-aware
run boundaries, warnings, failure or skip reasons, and stable artifact
identities without importing Review/History internals or changing Review JSON.

Phase 6 Package 2 adds the immutable typed pre-generation aggregate for current
portfolio, canonical ready current-state market analysis, Phase 4 external
context/sentiment, and Phase 5 ETF discovery, sector analysis, and screening.
Assembly enforces one cutoff, deterministic context ordering, unique and
associated sentiment, shared discovery universe identity, and explicit missing
optional evidence without recalculating upstream results.

Phase 6 Package 3 adds deterministic Review Package generation and atomic file
export from the typed integrated aggregate. It reuses the established portfolio,
stock-analysis, and external-context adapters plus Review schema version `1.0`,
projects Phase 5 evidence without granting ranking/recommendation authority, and
keeps missing evidence and cost-basis-only portfolio limitations visible.

Phase 6 Package 4 adds History-owned coordination of immutable archive
registration, manifest-to-SQLite metadata synchronization, and transactional
detail import. Successful archive and projection outcomes remain separate, and
projection failure identifies the registered canonical snapshot without
rewriting or deleting its archive bytes.

Phase 6 Package 5 adds deterministic, read-only selection of the nearest
earlier compatible snapshot with completed structured import. It reuses the
existing compatibility and comparison service, distinguishes `FIRST_RUN` from
`UNAVAILABLE`, and never fabricates a zero-change baseline.

Phase 6 Package 6 adds the user-facing `investment_terminal.cli.review`
composition root. It reuses the live typed market result, current portfolio
snapshot, integrated Review export, canonical History preservation/projection,
and deterministic comparison services, then persists the versioned workflow
report. A hermetic two-run E2E verifies first-run and comparison behavior with
no network, AI, Knowledge promotion, broker action, or trade execution.

The Phase 6 closure-readiness audit verifies all six success-path packages and
authority boundaries but records Phase 6 as `NOT CLOSED`. The command currently
constructs and writes a workflow report only after complete success; later
failure can therefore hide completed earlier work, dependent skips, or a
canonical archive registered before projection failure. The audit and bounded
remediation are recorded in `docs/PHASE_6_CLOSURE_AUDIT.md`.

The bounded closure remediation now builds all eight canonical stage outcomes
on handled operational failure, atomically persists the workflow report, and
only then exits non-zero. Completed artifacts remain visible;
`HistoricalProjectionAfterArchiveError` becomes completed archive, failed
projection, and skipped comparison outcomes without changing canonical bytes.

Phase 6 is closed after the repeated audit verified every roadmap package, the
failure-reporting remediation, authority boundaries, hermetic success/failure
paths, and the green full suite. The final record is
`docs/PHASE_6_CLOSURE.md`.

Audit document:

```text
docs/PROJECT_FULL_AUDIT.md
```

Product definition:

```text
docs/PROJECT_VISION.md
```

Development roadmap:

```text
docs/ROADMAP_AFTER_AUDIT.md
```

---

## Verified Product Direction

InvestmentTerminal is a personal investment intelligence platform.

Core flow:

```text
Market / external data
→ deterministic analysis
→ Review Package
→ immutable History
→ Knowledge
→ AI interpretation
→ explainable investment review
```

---

## Current Audit Conclusion

The architecture is suitable for further development.

Phase 1–6 architecture includes provider adapters, candle and analytical
repositories, maintained-universe and context boundaries, portfolio imports,
runtime backup/restore, integrated Review/History, and grounded-AI handoff.

The operational Phase 7 audit found no measured basis for claiming 20-year
candle coverage, an approximately 1000-company maintained universe, a loaded
real user portfolio, live external-context coverage, scheduled refreshes, or
real-data runtime/recovery performance. UI work is therefore moved to Phase 8.

Architecture redesign is not required.

---

## Working Protocol

Canonical package and operational handoff protocol:

```text
docs/AI_ASSISTED_DELIVERY_WORKFLOW.md
```

Every package uses an exact-baseline fresh clone, one primary package type, one
smallest coherent change, focused and full tests with repository-local
`--basetemp` where required, `git diff --check`, one conventional local commit,
and a verified structured ZIP. User-executed operational blocks explicitly mark
shareable and private paths.

---

## Latest Package

```text
Phase 7 Package 48 - Local-Only Candidate-Absence Diagnostic Audit
```

Files: `docs/PHASE_7_PACKAGE_48.md`, `docs/ROADMAP_AFTER_AUDIT.md`,
`Roadmap.md`, `NEXT_STEPS.md`, and `PROJECT_CONTINUATION.md`.

Source baseline verified exactly:

```text
develop @ 069a8fd43a60fc77d63a4c26961ba93677baab23
```

Result:

- the existing service already owns every fact needed to diagnose
  `CANDIDATE_TICKER_ABSENT` without another provider request;
- a separate schema-version-1 local-only diagnostic with an explicit output
  path is the smallest safe boundary;
- the shareable report remains schema version 3 and acceptance remains
  fail-closed;
- automatic correction, rerun, qualification, and valuation remain excluded.

Verification:

- focused OpenFIGI/privacy/architecture checks: 32 passed;
- complete local suite: 2,811 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package

```text
Phase 7 Package 31 - Exact-Repeat Private Transaction Import
```

Package 31 recorded the successful exact repeat: zero rows were inserted, all
62 submitted identities were duplicates, and stored total and occurrence bounds
were unchanged. Focused checks passed 59 tests and the complete suite passed
2,767 tests with four skipped.

---

## Previous Package 24

```text
Phase 7 Package 24 — Portfolio-Transaction Operational Input Audit
```

Source baseline verified exactly:

```text
develop @ 544ee79f5c231199339c780ee84481aea38c531b
```

The audit verified parser, import accounting, SQLite, privacy, and baseline
capabilities, then selected parse-only qualification because no transaction CLI
or redacted report existed and durable batch import was not atomic. Focused
checks passed 81 tests; the complete suite passed 2,743 tests with four skipped
and one existing Starlette warning.

---

## Previous Package 21

```text
Phase 7 Package 21 — Closure-Readiness Audit
```

Files:

```text
docs/PHASE_7_PACKAGE_21.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ 1c64a849e2e256f03140c57cc437368417045daa
```

Audit result:

- Phase 7 closure readiness: `NOT READY`;
- actual runtime SQLite integrity is `ok` with 3,766 daily candles:
  AAPL 1,254, IBM 1,254, and MSFT 1,258;
- the explicit MSFT refresh report is `READY`, so refresh observability and
  measured performance are `READY` for that bounded evidence only;
- current portfolio, transactions, valuations, maintained universe, external
  context, runtime backups, and workflow report remain `ABSENT`;
- per-series baseline freshness and the approximately 20-year/1000-company
  targets remain unmeasured;
- the current-portfolio operational input audit is the smallest safe next
  package; no private data write is authorized by this audit.

Verification:

- focused operational/portfolio/architecture checks: 58 passed;
- complete local suite: 2,743 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 20

```text
Phase 7 Package 20 — Refresh-Report Projection
```

Files:

```text
investment_terminal/operations/operational_data_baseline.py
investment_terminal/cli/operational_data_baseline.py
tests/test_operational_data_baseline.py
tests/test_operational_data_baseline_cli.py
docs/PHASE_7_PACKAGE_20.md
docs/ROADMAP_AFTER_AUDIT.md
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ e151a457ff8869119195c0ad03c7e0e7729a7613
```

Result:

- omitted refresh input preserves the exact schema-version-1 eight-store shape;
- an explicit valid report adds one deterministic `REFRESH_REPORT` store;
- valid `SUCCESS`, `NOT_READY`, and `FAILED` evidence is measured without
  inventing failed-result transfer counters;
- malformed, unsupported, inconsistent, naive-time, and invalid-duration
  evidence remains visible and cannot produce `READY`;
- read-only MSFT projection measured nine stores, `REFRESH_REPORT=READY`, and
  refresh/performance `READY` without modifying runtime evidence;
- scheduler, multi-instrument refresh, analysis, and trading remain excluded.

Verification:

- focused baseline/refresh/architecture checks: 44 passed;
- complete local suite: 2,743 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 19

```text
Phase 7 Package 19 — Refresh-Report Projection Audit
```

Files:

```text
docs/PHASE_7_PACKAGE_19.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ 1c0d247123d9a5d1aec11f4b2ba92e96dd181073
```

Audit result:

- baseline schema version 1 has eight deterministic stores by default;
- refresh/performance state currently derives only from workflow evidence;
- standalone refresh reports have no baseline input or projection;
- optional conditional `REFRESH_REPORT` is the smallest compatible seam;
- omitted input must preserve the exact existing default shape;
- invalid explicit input must be visible and must not produce `READY`;
- implementation and failure-path tests selected next;
- refresh execution, scheduler, and broader ingestion remain out of scope.

Verification:

- focused baseline/refresh/architecture checks: 40 passed;
- complete local suite: 2,731 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 18

```text
Phase 7 Package 18 — MSFT Already-Fresh Provider Bypass
```

Files:

```text
docs/PHASE_7_PACKAGE_18.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ 513cc311eea795ed63a7be74adf258c66951681f
```

Measured operational result:

- exact original MSFT checked-at repeated;
- status: `SUCCESS`; duration: 0.001261 seconds;
- before/after freshness: `FRESH` / `FRESH`;
- refresh not attempted; import null; all transfer counters zero;
- MSFT total remains 1,258; market total remains 3,766;
- SQLite integrity: `ok`;
- canonical baseline refresh projection remains absent;
- another instrument, scheduler, and mass refresh remain out of scope.

Verification:

- focused refresh/baseline/architecture checks: 71 passed;
- complete local suite: 2,731 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 17

```text
Phase 7 Package 17 — Live MSFT Refresh Measurement
```

Files:

```text
docs/PHASE_7_PACKAGE_17.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ 6ed92f05d92d0fa0431ba743f27695c68e48051d
```

Measured operational result:

- status: `SUCCESS`; duration: 1.149708 seconds;
- MSFT freshness: `STALE` to `FRESH`;
- 10 downloaded, four inserted, six duplicates;
- stored MSFT total: 1,258 through `2026-08-24T04:00:00Z`;
- market-store total: 3,766; SQLite integrity: `ok`;
- exact same-checked-at repeat selected next;
- another instrument, scheduler, and mass refresh remain out of scope.

Verification:

- focused CLI/freshness/refresh/baseline/architecture checks: 69 passed;
- complete local suite: 2,731 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 16

```text
Phase 7 Package 16 — Single-Instrument Refresh Observability
```

Files:

```text
investment_terminal/cli/market_data_refresh.py
tests/test_market_data_refresh_cli.py
docs/PHASE_7_PACKAGE_16.md
docs/ROADMAP_AFTER_AUDIT.md
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ 01b8a88c9030e168159c66a5bc51c644fab153a0
```

Architecture and behavior:

- one explicit instrument and checked-at time only;
- composes existing Yahoo, repository, freshness, and refresh boundaries;
- atomic schema-version-1 operational report;
- separate `SUCCESS`, `NOT_READY`, and `FAILED` outcomes;
- preserves before/after freshness, exact import evidence, and duration;
- provider/database failures and still-stale results exit non-zero;
- scheduler, retries, multi-instrument refresh, analysis, and trading excluded.

Verification:

- focused CLI/freshness/refresh/baseline/architecture checks: 69 passed;
- complete local suite: 2,731 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 15

```text
Phase 7 Package 15 — Measured-State Refresh Audit
```

Files:

```text
docs/PHASE_7_PACKAGE_15.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ 59a89b4d2c5c315fc74bd065ab8ea762a2c1fbcd
```

Measured audit result:

- market store: `READY`, 3,762 daily candles;
- MSFT, AAPL, and IBM each contain 1,254 candles over the same bounded window;
- per-series freshness: `UNMEASURED`;
- refresh observability and measured performance: `UNMEASURED`;
- refresh/freshness services exist, but no dedicated operational CLI/report;
- next package: bounded single-instrument refresh observability;
- scheduler, mass ingestion, and another instrument remain out of scope.

Verification:

- focused baseline/freshness/refresh/architecture checks: 66 passed;
- complete local suite: 2,726 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 14

```text
Phase 7 Package 14 — Controlled Five-Year IBM/XNYS History
```

Files:

```text
docs/PHASE_7_PACKAGE_14.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ e9a652abe3af7c2adc6cade6a9a713be8623bf83
```

Measured operational result:

- initial IBM ingestion: 1,254 inserted from 1,254 downloaded;
- exact repeat: zero inserted, 1,254 duplicates, stored total unchanged;
- IBM/XNYS coverage: 1,254 expected and observed sessions;
- missing and unexpected counts: zero; completeness: 1.0;
- SQLite integrity: `ok`;
- mass ingestion and another instrument remain out of scope.

Verification:

- focused ingestion/coverage/calendar/architecture checks: 31 passed;
- complete local suite: 2,726 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 13

```text
Phase 7 Package 13 — IBM Qualification Success Handoff
```

Files:

```text
docs/PHASE_7_PACKAGE_13.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified exactly:

```text
develop @ 69affb8ba7f3a31cadecaf8fea183e75b26341fd
```

Measured result and blocker:

- bounded IBM Yahoo qualification: `SUCCESS`, 1,254 daily candles;
- qualification failure: null;
- staged `XNYS@1` checksum verification: passed;
- pre-ingestion `IBM_TOTAL=0`; SQLite integrity: `ok`;
- runtime calendar is absent and this execution profile has no runtime write;
- no ingestion was attempted and operational SQLite was not modified.

Verification:

- focused qualification/evidence/ingestion/coverage/architecture checks:
  47 passed;
- complete local suite: 2,726 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 12

```text
Phase 7 Package 12 — XNYS Evidence Generation Checkpoint
```

Files:

```text
docs/PHASE_7_PACKAGE_12.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 8fde6a0fab31a0ae1ee891741dea158219b786a8
```

Measured result and blocker:

- `XNYS@1` generated 1,254 sessions and passed checksum verification;
- checksum is `83d70a90bb334fac740a209a20bcfbfcb685de805130655cfef31134ab48e2fb`;
- the operational SQLite contains zero IBM daily candles;
- runtime write access was unavailable and escalation was disabled;
- no IBM request was sent and the operational database was not modified.

Verification:

- focused evidence/ingestion/coverage/architecture checks: 35 passed;
- complete local suite: 2,726 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 11

```text
Phase 7 Package 11 — Bounded XNYS Session Evidence
```

Files:

```text
investment_terminal/cli/xnys_session_evidence.py
tests/test_xnys_session_evidence.py
docs/PHASE_7_PACKAGE_11.md
docs/ROADMAP_AFTER_AUDIT.md
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 1f2f46f80b5d52d3b7a0ac7d2f2db7a1701e0ca3
```

Architecture/product alignment:

- IBM is selected through explicit official `XNYS:IBM` identity;
- official ICE/NYSE schedules cover the complete bounded five-year window;
- the January 9, 2025 exceptional closure remains explicit;
- `XNYS@1` emits 1,254 sessions with its own provenance and checksum;
- IBM and mass ingestion remain out of scope for this package.

Verification:

- focused calendar/coverage/architecture checks: 56 passed;
- complete local suite: 2,726 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 10

```text
Phase 7 Package 10 — Controlled Second XNAS Instrument
```

Files:

```text
docs/PHASE_7_PACKAGE_10.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 9ff76a69c4cf0cdc2468ee35fac273eb15dadebe
```

Measured operational result:

- official Nasdaq evidence identifies AAPL as Nasdaq Listed;
- the operational SQLite contained zero AAPL daily candles before ingestion;
- 1,254 stored AAPL candles match 1,254 `XNAS@2` sessions;
- missing and unexpected counts are zero; completeness is 1.0;
- the exact repeat inserted zero rows and reported 1,254 duplicates;
- SQLite integrity is `ok`;
- mass ingestion remains out of scope.

Verification:

- focused operational/coverage/architecture checks: 34 passed;
- complete local suite: 2,724 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

---

## Previous Package 9

```text
Phase 7 Package 9 — Controlled Five-Year MSFT History
```

Files:

```text
investment_terminal/cli/xnas_session_evidence.py
investment_terminal/history/session_calendar_evidence.py
tests/test_xnas_session_evidence.py
docs/PHASE_7_PACKAGE_9.md
docs/ROADMAP_AFTER_AUDIT.md
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ b04990d1e2f35f1b38e404cc9728e582da74647d
```

Measured operational result:

- 1,254 stored MSFT daily candles match 1,254 `XNAS@2` sessions;
- missing and unexpected counts are zero; completeness is 1.0;
- the exact repeat inserted zero rows and reported 1,254 duplicates;
- SQLite integrity is `ok`;
- multi-instrument and mass ingestion remain out of scope.

Verification:

- focused coverage/calendar/architecture checks: 54 passed;
- complete local suite: 2,724 passed, 4 skipped;
- one existing Starlette deprecation warning and one sandbox pytest-cache warning;
- `git diff --check`: clean.

---

## Previous Package

```text
Phase 7 Package 5 — Explicit-Session Candle Coverage Quality
```

Files:

```text
investment_terminal/history/candle_coverage_quality.py
tests/test_candle_coverage_quality.py
docs/PHASE_7_PACKAGE_5.md
docs/ROADMAP_AFTER_AUDIT.md
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 9819ef92091626810f2d10407e8cc074b94a51a5
```

Architecture/product alignment:

- one-year MSFT ingestion stored 251 daily candles across 364 observed days;
- row count and elapsed span do not establish trading-session completeness;
- History-owned evaluation requires explicit versioned session evidence;
- missing sessions and unexpected candles remain visible and deterministic;
- calendar inference, bulk ingestion, analysis, and trading remain out of scope.

Verification:

- focused coverage, calendar, model, and architecture checks: 40 passed;
- complete local suite: 2720 passed, 4 skipped, 1 existing Starlette warning;
- `git diff --check`: clean.
