# Sprint 13 Review — Historical Query, Comparison, and Replay Foundation

**Sprint:** 13  
**Status:** Implementation complete; final local closure checks required  
**Theme:** Historical Query, Comparison, and Replay Foundation  
**Reviewed baseline:** `develop @ 65bb27b`

---

## Executive Summary

Sprint 13 transformed the History subsystem from a preservation/import foundation into a usable read-only historical intelligence interface.

The implemented flow is now:

```text
Immutable Review Package archive
        ↓
Append-only manifest
        ↓
Schema-managed SQLite History
        ↓
Explicit import state
        ↓
Typed historical repositories
        ↓
Timeline queries
        ↓
Compatibility assessment
        ↓
Snapshot comparison
        ↓
Exact / normalized replay
        ↓
Read-only CLI inspection
```

The sprint preserved the core governance rule:

```text
Archived Review Package JSON = canonical historical evidence
manifest.jsonl               = append-only navigation index
history.db                   = rebuildable structured projection
```

No Sprint 13 feature requires archive mutation, external market-data access, autonomous decisions, or current-code historical recalculation.

---

# 1. Delivered Capabilities

## 1.1 Historical query foundation

Implemented:

- canonical `HistoricalTimelineEvent`;
- typed timeline repository;
- chronological snapshot listing;
- package/date snapshot filters;
- latest snapshot lookup;
- previous/next snapshot navigation;
- repository-owned History persistence queries.

The CLI no longer needs direct SQLite knowledge for historical inspection.

## 1.2 Schema migration foundation

Implemented:

- explicit History SQLite migration objects;
- sequential migration execution;
- transactional migration behavior;
- future-version rejection;
- idempotent migration handling;
- schema version `1 → 2`;
- preservation of Sprint 12 History data.

Current History schema target:

```text
2
```

## 1.3 Explicit import-state workflow

Implemented canonical states:

```text
METADATA_ONLY
VERIFIED
IMPORTING
IMPORTED
FAILED
```

Import completion is no longer inferred from the existence of detail rows.

Manifest synchronization, verification, import execution, failure handling, retry, and legacy reconciliation now use explicit persisted state.

## 1.4 Atomic historical detail import

The import pipeline owns one SQLite transaction for:

```text
portfolio_summary
→ holdings
→ recommendations
→ deployment
→ timeline_events
```

Detail writers may use a caller-owned connection while retaining their standalone behavior.

Controlled interruption and retry are covered without deleting snapshot metadata.

## 1.5 Verified historical byte ownership

Archive verification now owns the read-once byte buffer.

The supported path is:

```text
resolve confined archive path
→ read bytes once
→ hash those bytes
→ return verified bytes
→ decode / parse the same bytes
```

The former verify-then-reread TOCTOU boundary has been removed.

## 1.6 Historical comparison foundation

Implemented typed read models and repositories for:

- portfolio summary;
- holdings;
- recommendations;
- deployment;
- compatibility facts.

Implemented comparators for:

- scalar values;
- portfolio summary;
- holdings;
- recommendations;
- deployment.

Collection identity uses persisted stable keys. Sprint 13 does not fuzzy-match different keys.

## 1.7 Snapshot compatibility

Implemented compatibility states:

```text
COMPATIBLE
PARTIALLY_COMPATIBLE
INCOMPATIBLE
```

Hard incompatibilities include:

- same or invalid snapshot chronology;
- unsupported package schema;
- portfolio identity mismatch;
- base-currency mismatch.

Soft limitations remain visible, including:

- source-status differences;
- incomplete structured details;
- non-`IMPORTED` state.

`INCOMPATIBLE` prevents misleading leaf comparisons.

## 1.8 Aggregate snapshot comparison

`HistoricalSnapshotComparisonService` now provides one application boundary for:

```text
snapshot resolution
→ import-state/facts lookup
→ compatibility
→ portfolio summary comparison
→ holdings comparison
→ recommendations comparison
→ deployment comparison
→ SnapshotComparison
```

The service is read-only and deterministic.

Simple value differences are not presented as investment performance.

## 1.9 Historical replay

Implemented replay models:

```text
EXACT_ARCHIVED_PACKAGE
NORMALIZED_HISTORICAL_VIEW
CURRENT_CODE_RECALCULATION
```

Sprint 13 implements only:

```text
EXACT_ARCHIVED_PACKAGE
NORMALIZED_HISTORICAL_VIEW
```

Exact replay uses the verified archived Review Package.

Normalized replay uses typed SQLite repositories and explicitly identifies itself as a rebuildable projection.

`CURRENT_CODE_RECALCULATION` remains intentionally unsupported.

## 1.10 History CLI

Implemented read-only CLIs:

```text
investment_terminal.cli.query_history
investment_terminal.cli.compare_history
investment_terminal.cli.replay_history
```

Capabilities include:

- human-readable output;
- complete JSON output;
- custom database/history paths;
- snapshot and timeline filtering;
- compatibility reporting;
- source-status warnings;
- exact and normalized replay.

CLI modules remain composition/rendering boundaries and do not own SQL or comparison/replay business logic.

## 1.11 Real end-to-end fixture

Sprint 13 includes a deterministic two-snapshot fixture covering:

```text
realistic Review Package
→ archive
→ manifest
→ migration
→ SQLite synchronization
→ verified atomic import
→ timeline
→ query CLI
→ comparison CLI
→ exact replay
→ normalized replay
```

The fixture is network-free and includes meaningful changes in:

- portfolio values;
- holdings;
- recommendations;
- deployment;
- source status.

---

# 2. Architecture Review

## 2.1 Source-of-truth boundary

**Assessment: PASS**

The implementation preserves the intended hierarchy:

```text
Archive = evidence
Manifest = index
SQLite = projection
```

Comparison consumes normalized historical facts.

Exact replay returns verified archive evidence.

Normalized replay never claims to be exact evidence.

## 2.2 Dependency direction

**Assessment: PASS**

Architecture tests protect:

- non-CLI modules from importing CLI;
- upstream analytical domains from importing History;
- upstream domains from importing Review.

Sprint 13 comparison and replay remain downstream History capabilities.

## 2.3 Persistence ownership

**Assessment: PASS**

History persistence queries are behind History repositories.

Multi-table detail import has one transaction owner at pipeline level.

Read-only CLIs do not contain direct SQL.

## 2.4 Immutability

**Assessment: PASS**

Sprint 13 does not weaken:

- exclusive archive creation;
- append-only manifest behavior;
- checksum identity;
- snapshot lineage;
- immutable original historical evidence.

Corrections remain new snapshots rather than archive rewrites.

## 2.5 Determinism

**Assessment: PASS**

Implemented models/repositories/comparators use:

- stable ordering;
- stable persisted identity keys;
- timezone-aware timestamps;
- explicit missing-data semantics;
- deterministic serialized results.

## 2.6 Evidence semantics

**Assessment: PASS**

The implementation keeps separate:

- exact archived evidence;
- normalized historical projection;
- comparison results;
- future recalculation concepts.

This prevents historical interpretation from being silently represented as original evidence.

---

# 3. Schema Migration Review

## 3.1 Migration objective

Sprint 13 required a safe transition:

```text
schema 1
→ schema 2
```

with explicit snapshot import state.

**Assessment: PASS**

## 3.2 Migration guarantees

Implemented migration behavior covers:

- current-version detection;
- sequential application;
- transactional execution;
- repeated-run safety;
- future-version rejection;
- preservation of existing historical rows;
- no archive mutation;
- no manifest mutation.

## 3.3 Legacy reconciliation

Existing snapshots can be reconciled into explicit import state rather than forcing users to delete or rebuild normal Sprint 12 databases manually.

**Assessment: PASS**

---

# 4. Definition of Done Assessment

| Sprint 13 requirement | Status |
|---|---|
| Public snapshot listing repository API | PASS |
| Typed timeline event model | PASS |
| Timeline repository queries | PASS |
| SQLite migration 1 → 2 | PASS |
| Explicit persisted import state | PASS |
| Existing import workflows use import state | PASS |
| Two snapshots can be compared | PASS |
| Portfolio differences represented | PASS |
| Holdings differences represented | PASS |
| Recommendation differences represented | PASS |
| Deployment differences represented | PASS |
| Exact archived replay | PASS |
| Normalized replay | PASS |
| Query CLI | PASS |
| Comparison CLI | PASS |
| Replay CLI | PASS |
| Realistic end-to-end fixture | PASS |
| Canonical documentation update | PASS |
| Sprint 13 review document | PASS with this package |
| Full regression suite | REQUIRES FINAL LOCAL RUN |
| Clean Git working tree | REQUIRES FINAL LOCAL CHECK |
| All changes committed and pushed | REQUIRES THIS PACKAGE COMMIT |

The implementation requirements are complete.

Formal sprint closure therefore depends only on repository-state checks that must be performed in the developer environment:

```powershell
python -m pytest -q
git status --short
```

No passing-test count is hard-coded in this document.

---

# 5. Constitution / Governance Assessment

Sprint 13 is consistent with the binding project principles.

## Evidence before opinion

Comparison operates on persisted facts and exposes missing/incompatible evidence.

## Python structures, AI interprets, humans decide

Historical query, comparison, and replay are deterministic Python capabilities. They do not create autonomous investment decisions.

## Explainability over complexity

Compatibility notes, source status, explicit change types, replay mode, checksum provenance, and warnings remain visible.

## Data quality and integrity

Checksum verification, archive confinement, exact-byte ownership, schema identity, import state, migrations, and transaction boundaries protect historical evidence.

## Historical discipline

The archive remains immutable and authoritative. Derived SQLite structures remain rebuildable.

**Governance verdict: PASS**

---

# 6. Deferred Scope

The following are intentionally not part of Sprint 13:

- `CURRENT_CODE_RECALCULATION`;
- historical external-data replay;
- recommendation outcome tracking;
- future-price performance windows;
- portfolio performance attribution;
- confidence calibration from outcomes;
- factor-effectiveness analysis;
- Knowledge Domain;
- AI-generated historical conclusions;
- dashboard/web UI;
- broker execution;
- autonomous trading;
- tax-lot history;
- multi-currency historical conversion.

These are deferred product capabilities, not incomplete Sprint 13 work.

---

# 7. Technical Debt and Follow-up

## 7.1 Project-status governance drift

`docs/PROJECT_STATUS.md` still describes early Sprint 13 architecture stabilization and lists historical query/comparison/replay work as in progress.

This is now stale relative to the implemented repository and the canonical documentation updated in Task 21.

Recommended follow-up:

```text
Update PROJECT_STATUS.md when Sprint 13 is formally closed.
```

This does not block the Sprint 13 implementation Definition of Done because Task 21 named the canonical product documents explicitly, but it should be reconciled before Sprint 14 planning begins.

## 7.2 Sprint 12 review is historical

`docs/SPRINT_12_REVIEW.md` correctly records the state at Sprint 12 closure, including features that were future work at that time.

It should not be rewritten to make its historical assessment look current.

Sprint 13 review supersedes those follow-up items where implemented.

## 7.3 Future repository protocols

Concrete repository construction remains acceptable for the current modular monolith.

Protocols/interfaces may be introduced later only where they solve a demonstrated testing or substitution problem.

## 7.4 Structured exception hierarchy

History currently uses explicit validation/runtime errors that CLIs translate into actionable errors.

A larger exception taxonomy may be useful later, but it is not required for Sprint 13 correctness.

---

# 8. Risk Review

## Schema migration damage

Mitigated through transactional migration tests and explicit version ownership.

## Partial historical import

Mitigated through pipeline-owned atomic detail transaction and explicit failure state.

## Archive TOCTOU

Mitigated through read-once verified bytes.

## Ambiguous comparison

Mitigated through compatibility assessment, stable keys, explicit missing-data semantics, and no performance claims from raw value deltas.

## Replay confusion

Mitigated through explicit replay modes and visible normalized-projection warnings.

## CLI architecture leakage

Mitigated through repository/service boundaries and architecture tests.

---

# 9. Recommended Sprint 14 Direction

Sprint 14 should not reopen Sprint 13 storage/replay foundations without evidence of a defect.

The next coherent product direction is:

## Outcome-aware Historical Intelligence

Candidate sequence:

1. define historical outcome questions before new metrics;
2. define explicit observation windows;
3. add recommendation-outcome models;
4. distinguish price movement from portfolio performance;
5. track recommendation transitions over time;
6. measure evidence coverage and decision stability;
7. add confidence calibration only after sufficient historical samples exist;
8. begin Knowledge Domain work only after outcome semantics are stable.

Guardrails:

- no hindsight leakage;
- no rewriting archived evidence;
- no unsupported causality claims;
- no false precision from small samples;
- no external-data historical reconstruction without explicit provenance/version contracts.

---

# 10. Final Sprint 13 Verdict

## Implementation

**COMPLETE**

## Architecture

**APPROVED**

## Historical integrity

**APPROVED**

## Schema migration

**APPROVED**

## Comparison foundation

**APPROVED**

## Replay foundation

**APPROVED**

## Documentation

**COMPLETE**, with `PROJECT_STATUS.md` reconciliation recommended as immediate post-review governance cleanup.

## Formal closure

**READY FOR FINAL LOCAL VERIFICATION**

Run:

```powershell
python -m pytest -q
git status --short
```

If the full suite is green and the working tree contains only this review file before commit, Sprint 13 may be formally closed after commit and push.

---

> Sprint 12 taught Investment Terminal to preserve history. Sprint 13 taught it to query, compare, and replay that history without weakening the evidence it depends on.
