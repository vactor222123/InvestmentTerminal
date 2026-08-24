# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint

**Current repository:** `vactor222123/InvestmentTerminal`
**Current branch:** `develop`
**Current GitHub baseline:** `69affb8ba7f3a31cadecaf8fea183e75b26341fd`
**Current local package:** Phase 7 Package 13 — IBM Operational Preflight
**Current phase:** Phase 7 — Operational Data and First Real Use — OPEN
**Current next action:** Restore Yahoo HTTPS, repeat IBM qualification, then ingest

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

Before every code package:

1. Read current files from GitHub.
2. Perform focused audit only for affected subsystem.
3. Analyze real repository state only.
4. Do not make assumptions.
5. Validate against PROJECT_VISION.md and architecture.
6. Provide complete changed files.
7. Update this checkpoint document.

After implementation:

- git add
- commit
- tests
- CI analysis after user confirmation.

---

## Latest Package

```text
Phase 7 Package 13 — IBM Operational Preflight
```

Files:

```text
docs/PHASE_7_PACKAGE_13.md
docs/ROADMAP_AFTER_AUDIT.md
Roadmap.md
NEXT_STEPS.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ 69affb8ba7f3a31cadecaf8fea183e75b26341fd
```

Measured result and blockers:

- staged `XNYS@1` passes checksum verification;
- IBM Yahoo qualification failed before persistence with curl error 7;
- outbound `fc.yahoo.com:443` was unavailable;
- runtime write access remains unavailable;
- no IBM candle was downloaded or stored.

Verification:

- focused qualification/evidence/ingestion/architecture suite: 43 passed;
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
