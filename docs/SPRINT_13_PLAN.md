# Sprint 13 Plan — Historical Query, Comparison, and Replay Foundation

**Sprint:** 13  
**Status:** Planned  
**Theme:** Historical Query, Comparison, and Replay Foundation  
**Depends on:** Sprint 12 — Historical Intelligence Foundation

---

# 1. Sprint Goal

Transform the History Domain from a storage and import foundation into a usable historical intelligence interface.

Sprint 13 will add the first public services for:

- querying historical snapshots;
- querying timeline events;
- tracking explicit import state;
- comparing two compatible snapshots;
- defining safe historical replay semantics;
- exposing these capabilities through CLI commands.

The sprint must build on the immutable archive, append-only manifest, SQLite history database, import pipeline, and timeline events created in Sprint 12.

---

# 2. Product Outcome

At the end of Sprint 13, Investment Terminal should be able to answer questions such as:

- Which historical snapshots exist?
- What happened during a selected review?
- Which events occurred for a symbol or portfolio?
- What changed between two snapshots?
- Which holdings were added or removed?
- Which recommendations changed?
- Was a snapshot fully imported or only registered as metadata?
- Can the exact historical Review Package be replayed safely?
- What is historical evidence, and what is a recalculation using current code?

The sprint does not yet attempt advanced performance attribution, recommendation outcome analysis, or knowledge extraction.

---

# 3. Architectural Context

Sprint 12 established:

```text
Review Package
        ↓
Immutable Archive
        ↓
Append-only Manifest
        ↓
Verified Loading
        ↓
Structured SQLite Import
        ↓
Timeline Events
```

Sprint 13 extends the flow:

```text
Structured History
        ↓
Public Query Services
        ↓
Snapshot Comparison
        ↓
Historical Replay Contract
        ↓
CLI Inspection
```

---

# 4. Scope

Sprint 13 includes:

1. public snapshot query repository improvements;
2. public timeline repository;
3. explicit snapshot import-state model;
4. SQLite schema migration foundation;
5. snapshot-comparison models;
6. portfolio-summary comparison;
7. holdings comparison;
8. recommendation comparison;
9. deployment comparison;
10. combined snapshot-comparison service;
11. historical replay request and result models;
12. replay service for exact archived evidence;
13. History query and comparison CLI;
14. real end-to-end History fixture and tests;
15. documentation updates;
16. Sprint 13 review.

---

# 5. Explicit Non-Goals

Sprint 13 will not implement:

- recommendation outcome tracking;
- future-price performance windows;
- confidence calibration;
- factor-effectiveness analysis;
- Knowledge Domain;
- AI-generated historical conclusions;
- autonomous trading;
- broker integration;
- dashboard or web UI;
- portfolio performance attribution;
- tax-lot history;
- multi-currency historical conversion;
- archive mutation;
- deletion of historical facts.

These belong to later sprints.

---

# 6. Core Design Principles

Sprint 13 must preserve the following rules:

1. Archived Review Package JSON remains canonical evidence.
2. Manifest remains append-only.
3. SQLite remains a rebuildable projection.
4. Query services never mutate historical data.
5. Comparison services never invent absent facts.
6. Replay must distinguish exact evidence from recalculation.
7. All persistent timestamps remain timezone-aware.
8. CLI contains orchestration only.
9. Public repositories replace direct SQL access from CLI.
10. Schema changes require explicit migration support.
11. Repeated commands remain safe.
12. All results must be deterministic and serializable.

---

# 7. Proposed Task Sequence

## Task 1 — Historical Snapshot Query Repository

### Goal

Extend the snapshot repository with a complete public query API.

### Proposed Methods

```python
list_all()
find_by_package_id(package_id)
find_generated_between(start, end)
latest()
previous_before(snapshot_id)
next_after(snapshot_id)
```

### Requirements

- deterministic chronological order;
- no direct SQL in CLI;
- timezone-aware date boundaries;
- immutable returned models;
- focused tests.

### Deliverables

```text
investment_terminal/history/historical_snapshot_repository.py
tests/test_historical_snapshot_repository.py
```

---

## Task 2 — Historical Timeline Event Model

### Goal

Introduce a canonical typed representation for timeline rows.

### Proposed Model

```text
HistoricalTimelineEvent
```

### Fields

- event ID;
- snapshot ID;
- event type;
- occurred at;
- subject key;
- parsed payload.

### Requirements

- timezone-aware timestamp;
- valid non-empty event type;
- valid snapshot UUID;
- JSON-object payload;
- immutable dataclass;
- `to_dict()` support.

### Deliverables

```text
investment_terminal/history/historical_timeline_models.py
tests/test_historical_timeline_models.py
```

---

## Task 3 — Historical Timeline Repository

### Goal

Provide public timeline queries without exposing raw SQLite.

### Proposed Methods

```python
list_for_snapshot(snapshot_id)
find_by_type(event_type)
find_by_subject(subject_key)
find_between(start, end)
latest(limit)
count()
```

### Requirements

- deterministic ordering;
- bounded result support;
- typed event results;
- no mutation;
- explicit validation;
- indexed query usage.

### Deliverables

```text
investment_terminal/history/historical_timeline_repository.py
tests/test_historical_timeline_repository.py
```

---

## Task 4 — Schema Migration Foundation

### Goal

Introduce controlled SQLite schema evolution before adding Sprint 13 tables.

### Proposed Components

```text
HistoricalSchemaMigration
HistoricalSchemaMigrator
```

### Requirements

- detect current schema version;
- apply migrations sequentially;
- reject unsupported future versions;
- execute each migration transactionally;
- record resulting schema version;
- remain idempotent;
- preserve existing Sprint 12 databases.

### Initial Migration

```text
schema version 1 → schema version 2
```

### Deliverables

```text
investment_terminal/history/historical_schema_migrations.py
tests/test_historical_schema_migrations.py
```

---

## Task 5 — Snapshot Import-State Model

### Goal

Stop inferring import completion from the presence of detail rows.

### Proposed Model

```text
HistoricalImportState
```

### Proposed Statuses

```text
METADATA_ONLY
VERIFIED
IMPORTING
IMPORTED
FAILED
```

### Proposed Fields

- snapshot ID;
- status;
- metadata synchronized at;
- package verified at;
- details imported at;
- timeline built at;
- importer version;
- failure reason;
- updated at.

### Requirements

- explicit state transitions;
- timezone-aware timestamps;
- no transition from completed state to an earlier state without a controlled reset;
- failure details remain visible;
- import pipeline updates state.

### Deliverables

```text
investment_terminal/history/historical_import_state_models.py
tests/test_historical_import_state_models.py
```

---

## Task 6 — Import-State Repository

### Goal

Persist and query `HistoricalImportState`.

### Proposed Methods

```python
get(snapshot_id)
require(snapshot_id)
initialize_metadata(snapshot)
mark_verified(snapshot_id)
mark_importing(snapshot_id)
mark_imported(snapshot_id)
mark_failed(snapshot_id, reason)
```

### Requirements

- valid state transitions;
- foreign key to snapshots;
- one state row per snapshot;
- transactional updates;
- focused tests.

### Deliverables

```text
investment_terminal/history/historical_import_state_repository.py
tests/test_historical_import_state_repository.py
```

---

## Task 7 — Integrate Import State with Existing Workflows

### Goal

Update manifest synchronization and historical import pipeline to use explicit import state.

### Required Changes

- manifest synchronization creates `METADATA_ONLY`;
- verified loading records `VERIFIED`;
- pipeline records `IMPORTING`;
- successful pipeline records `IMPORTED`;
- failed pipeline records `FAILED`;
- repeat-import checks use state rather than detail-row inference;
- existing databases migrate safely.

### Deliverables

```text
investment_terminal/history/historical_manifest_import_service.py
investment_terminal/history/historical_import_pipeline.py
tests/test_historical_manifest_import_service.py
tests/test_historical_import_pipeline.py
```

---

## Task 8 — Snapshot Comparison Models

### Goal

Define immutable models for comparison results.

### Proposed Models

```text
SnapshotComparison
PortfolioSummaryChange
HoldingChange
RecommendationChange
DeploymentChange
```

### Required Concepts

- earlier snapshot ID;
- later snapshot ID;
- compatibility status;
- added;
- removed;
- changed;
- unchanged where useful;
- previous value;
- current value;
- absolute change;
- percentage change where valid.

### Requirements

- no implicit compatibility;
- no division by zero;
- explicit absent-value semantics;
- deterministic ordering;
- serializable output.

### Deliverables

```text
investment_terminal/history/historical_comparison_models.py
tests/test_historical_comparison_models.py
```

---

## Task 9 — Snapshot Compatibility Service

### Goal

Determine whether two snapshots may be meaningfully compared.

### Proposed Checks

- snapshot IDs differ;
- earlier generated time precedes later generated time;
- package schemas are supported;
- portfolio identity matches when available;
- base currency matches;
- source-status differences are exposed;
- missing detail tables are visible.

### Proposed Result

```text
SnapshotCompatibilityResult
```

### Deliverables

```text
investment_terminal/history/historical_snapshot_compatibility.py
tests/test_historical_snapshot_compatibility.py
```

---

## Task 10 — Portfolio Summary Comparator

### Goal

Compare normalized portfolio summaries.

### Compare

- total value;
- invested value;
- cash value;
- monthly contribution;
- source status;
- cash weight;
- invested weight.

### Requirements

- explicit missing-summary handling;
- currency compatibility;
- source-status visibility;
- no performance claims from simple value differences.

### Deliverables

```text
investment_terminal/history/historical_portfolio_summary_comparator.py
tests/test_historical_portfolio_summary_comparator.py
```

---

## Task 11 — Holdings Comparator

### Goal

Compare historical holdings using stable holding keys.

### Detect

- holdings added;
- holdings removed;
- quantity changes;
- unit-price changes;
- value changes;
- weight changes;
- sleeve changes;
- strategy changes.

### Requirements

- stable deterministic ordering;
- identity based on holding key;
- original snapshots remain unchanged;
- missing holdings remain explicit.

### Deliverables

```text
investment_terminal/history/historical_holdings_comparator.py
tests/test_historical_holdings_comparator.py
```

---

## Task 12 — Recommendations Comparator

### Goal

Compare machine recommendations between snapshots.

### Detect

- recommendation added;
- recommendation removed;
- action transition;
- score change;
- confidence change;
- rationale change;
- payload change.

### Identity

Preferred:

```text
stable recommendation key
```

Fallback comparison rules must be explicit and documented.

### Deliverables

```text
investment_terminal/history/historical_recommendations_comparator.py
tests/test_historical_recommendations_comparator.py
```

---

## Task 13 — Deployment Comparator

### Goal

Compare historical allocation and deployment records.

### Detect

- deployment item added;
- deployment item removed;
- amount change;
- share change;
- rationale change;
- payload change.

### Deliverables

```text
investment_terminal/history/historical_deployment_comparator.py
tests/test_historical_deployment_comparator.py
```

---

## Task 14 — Historical Snapshot Comparison Service

### Goal

Combine all comparison components into one application service.

### Workflow

```text
Earlier snapshot
        +
Later snapshot
        ↓
Compatibility validation
        ↓
Portfolio summary comparison
        ↓
Holdings comparison
        ↓
Recommendations comparison
        ↓
Deployment comparison
        ↓
SnapshotComparison
```

### Requirements

- read-only;
- deterministic;
- no direct archive mutation;
- structured result;
- useful partial comparison when supported;
- explicit limitations.

### Deliverables

```text
investment_terminal/history/historical_snapshot_comparison_service.py
tests/test_historical_snapshot_comparison_service.py
```

---

## Task 15 — Historical Replay Models

### Goal

Define exactly what “replay” means.

### Proposed Replay Modes

```text
EXACT_ARCHIVED_PACKAGE
NORMALIZED_HISTORICAL_VIEW
CURRENT_CODE_RECALCULATION
```

Sprint 13 must implement only the first two modes.

`CURRENT_CODE_RECALCULATION` should remain defined but unsupported until its inputs and compatibility rules are mature.

### Proposed Models

```text
HistoricalReplayRequest
HistoricalReplayResult
```

### Requirements

- explicit replay mode;
- source snapshot ID;
- package schema;
- evidence checksum;
- replay warnings;
- no implication that current external context existed historically.

### Deliverables

```text
investment_terminal/history/historical_replay_models.py
tests/test_historical_replay_models.py
```

---

## Task 16 — Historical Replay Service

### Goal

Provide safe access to exact historical evidence and normalized historical views.

### Supported Behavior

#### Exact Archived Package

- load through verified package loader;
- return exact parsed payload;
- expose snapshot metadata and checksum;
- never recalculate.

#### Normalized Historical View

- load snapshot;
- portfolio summary;
- holdings;
- recommendations;
- deployment;
- timeline events;
- import state.

### Requirements

- read-only;
- verified archive requirement;
- structured warnings;
- explicit unsupported-mode error;
- no external data access.

### Deliverables

```text
investment_terminal/history/historical_replay_service.py
tests/test_historical_replay_service.py
```

---

## Task 17 — History Query CLI

### Goal

Expose snapshot and timeline queries through CLI.

### Proposed Module

```text
investment_terminal/cli/query_history.py
```

### Proposed Commands

```powershell
python -m investment_terminal.cli.query_history snapshots
python -m investment_terminal.cli.query_history timeline
python -m investment_terminal.cli.query_history show --snapshot-id <uuid>
```

### Requirements

- human-readable output;
- `--json` support;
- custom database path;
- date and event filters;
- no direct SQL;
- actionable errors.

---

## Task 18 — Snapshot Comparison CLI

### Goal

Compare two snapshots from the command line.

### Proposed Module

```text
investment_terminal/cli/compare_history.py
```

### Example

```powershell
python -m investment_terminal.cli.compare_history `
    --earlier <snapshot-uuid> `
    --later <snapshot-uuid>
```

### Requirements

- human-readable summary;
- complete `--json` output;
- compatibility errors;
- clear source-status warnings;
- no business logic inside CLI.

---

## Task 19 — Historical Replay CLI

### Goal

Expose supported replay modes.

### Proposed Module

```text
investment_terminal/cli/replay_history.py
```

### Examples

```powershell
python -m investment_terminal.cli.replay_history `
    --snapshot-id <uuid> `
    --mode exact
```

```powershell
python -m investment_terminal.cli.replay_history `
    --snapshot-id <uuid> `
    --mode normalized `
    --json
```

---

## Task 20 — Real End-to-End History Fixture

### Goal

Test Sprint 12 and Sprint 13 using a Review Package shaped like real product output.

### Required Flow

```text
Realistic Review Package fixture
        ↓
Archive
        ↓
Manifest
        ↓
SQLite synchronization
        ↓
Verified import
        ↓
Timeline
        ↓
Query
        ↓
Comparison
        ↓
Replay
```

### Requirements

- no network;
- deterministic timestamps and UUIDs;
- realistic portfolio, recommendations, and deployment;
- two snapshots with meaningful differences;
- complete integration assertions.

---

## Task 21 — Documentation Update

Update:

```text
README.md
ARCHITECTURE.md
DATA_MODEL.md
DOMAIN_MAP.md
DESIGN_PRINCIPLES.md
QUALITY_ATTRIBUTES.md
Roadmap.md
GLOSSARY.md
```

Add CLI usage and new persistent models.

If SQLite schema changes, document schema version 2 and migration behavior.

---

## Task 22 — Sprint 13 Review

Create:

```text
docs/SPRINT_13_REVIEW.md
```

The review must include:

- delivered capabilities;
- architecture review;
- schema migration review;
- Definition of Done assessment;
- deferred scope;
- technical debt;
- recommended Sprint 14 direction.

---

# 8. Proposed Commit Strategy

Use focused commits.

Examples:

```text
feat(history): add timeline event model
feat(history): add timeline repository
feat(history): add schema migration foundation
feat(history): add import state model
feat(history): integrate import state pipeline
feat(history): add snapshot comparison models
feat(history): add portfolio summary comparator
feat(history): add holdings comparator
feat(history): add recommendations comparator
feat(history): add deployment comparator
feat(history): add snapshot comparison service
feat(history): add replay models
feat(history): add replay service
feat(cli): add history query command
feat(cli): add history comparison command
feat(cli): add history replay command
test(history): add end-to-end historical intelligence fixture
docs(history): update documentation after sprint 13
docs(history): add sprint 13 review
```

One logical responsibility should normally equal one commit.

---

# 9. Testing Strategy

Each task requires focused tests.

The full suite must be run after every completed logical block.

## Required Test Categories

- model validation;
- repository ordering;
- timeline filtering;
- migration from schema 1 to schema 2;
- migration idempotence;
- import-state transitions;
- pipeline failure state;
- comparison added/removed/changed cases;
- zero-value percentage handling;
- compatibility failures;
- replay integrity;
- replay unsupported mode;
- CLI JSON output;
- end-to-end workflow;
- regression suite.

## Commands

Focused test:

```powershell
python -m pytest tests\<test_file>.py
```

Full suite:

```powershell
python -m pytest
```

---

# 10. Migration Requirements

Sprint 13 is expected to introduce SQLite schema version 2.

Migration must:

- preserve all Sprint 12 rows;
- create the import-state table;
- populate reasonable initial state for existing snapshots;
- avoid archive or manifest changes;
- run transactionally;
- fail visibly;
- remain safe on repeated startup.

No manual database deletion should be required for a normal upgrade.

---

# 11. Backward Compatibility

Sprint 13 must remain compatible with:

- Sprint 12 archived JSON;
- Sprint 12 manifest records;
- Sprint 12 SQLite schema through migration;
- existing Review Package schema 1.0;
- existing archive and import CLI workflows.

Public CLI commands from Sprint 12 must continue working unless a documented migration requires a controlled change.

---

# 12. Security and Integrity Requirements

- archive paths remain constrained to history root;
- replay requires checksum verification;
- query services remain read-only;
- comparison never modifies source rows;
- migration does not touch archived JSON;
- manifest remains append-only;
- SQL parameters remain bound;
- payload JSON remains valid;
- errors do not expose secrets.

---

# 13. Performance Expectations

Sprint 13 is local-first.

Expected dataset size remains moderate, but queries should use indexes.

Add indexes where required for:

- timeline event type;
- timeline subject key;
- timeline occurred time;
- import-state status;
- snapshot generated time.

Optimization must be based on query behavior rather than speculation.

---

# 14. Definition of Done

Sprint 13 is complete when:

- snapshot listing has a public repository API;
- timeline events have a typed model;
- timeline queries work through a repository;
- SQLite migration from schema 1 to 2 works;
- explicit import state is stored;
- existing import workflows use import state;
- two snapshots can be compared;
- portfolio, holdings, recommendations, and deployment differences are represented;
- exact archived replay works;
- normalized replay works;
- query, comparison, and replay CLIs work;
- realistic end-to-end tests pass;
- full regression tests pass;
- documentation is updated;
- `SPRINT_13_REVIEW.md` is written;
- Git working tree is clean;
- all changes are committed and pushed.

---

# 15. Risks

## Risk 1 — Sprint Scope Is Too Large

Mitigation:

- keep comparators independent;
- defer outcome analysis;
- defer current-code recalculation replay;
- stop after a stable read-only comparison foundation if necessary.

## Risk 2 — Schema Migration Damages Existing Databases

Mitigation:

- transactional migrations;
- migration tests using copied schema-1 databases;
- no archive or manifest mutation;
- version checks before migration.

## Risk 3 — Comparison Semantics Become Ambiguous

Mitigation:

- explicit compatibility result;
- separate missing, added, removed, and changed states;
- no performance claims from simple value changes;
- preserve source-status information.

## Risk 4 — Replay Is Misunderstood

Mitigation:

- explicit replay modes;
- exact archived evidence as default;
- unsupported current-code recalculation in Sprint 13;
- visible warnings.

## Risk 5 — CLI Starts Duplicating Domain Logic

Mitigation:

- repositories and services first;
- CLI only configures and renders;
- focused CLI tests.

---

# 16. Recommended Start Sequence

Begin Sprint 13 only after Sprint 12 closure checks:

```powershell
python -m pytest
git status
```

Then create the Sprint 13 planning commit:

```powershell
git add docs/SPRINT_13_PLAN.md
git commit -m "docs(history): add sprint 13 plan"
git push origin develop
```

Implementation should begin with:

```text
Task 1 — Historical Snapshot Query Repository
```

This removes direct snapshot-table access from the CLI and creates the clean query foundation needed by every later Sprint 13 task.

---

# 17. Sprint Statement

> Sprint 12 taught Investment Terminal how to preserve history. Sprint 13 will teach it how to inspect, compare, and replay that history safely.
