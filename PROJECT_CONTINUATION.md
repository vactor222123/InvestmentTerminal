# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint

**Current repository:** `vactor222123/InvestmentTerminal`
**Current branch:** `develop`
**Current GitHub baseline:** `d8678283aa695e4b7fd6a2c3f980f5984eb34efe`
**Current local package:** Phase 5 Package 7
**Current phase:** Phase 5 — Market Discovery
**Current next action:** Apply Phase 5 Package 7, then audit Phase 5 roadmap closure

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

Main missing product capabilities:

- multi-asset intelligence
- ETF intelligence
- transaction-based portfolio history
- portfolio risk/rebalancing
- macro/news context
- market discovery
- user interface
- broker integrations

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
Phase 5 Package 7 — Deterministic Screening Pipeline
```

Files:

```text
investment_terminal/universe/screening_pipeline.py
tests/test_screening_pipeline.py
DataModel.md
PROJECT_CONTINUATION.md
```

Source baseline verified against GitHub:

```text
develop @ d8678283aa695e4b7fd6a2c3f980f5984eb34efe
```

Architecture/product alignment:

- screening criteria are versioned, effective-dated, and fully caller-owned;
- every universe member receives deterministic PASS, FAIL, or REVIEW evidence;
- evidence identifiers, observed values, thresholds, operators, and units remain traceable;
- missing metrics follow explicit policy and unit mismatches fail closed;
- duplicate, future, irrelevant, and out-of-universe metrics fail closed;
- screening does not rank, recommend, or authorize execution;
- Phase 5 roadmap closure is the next focused audit.
