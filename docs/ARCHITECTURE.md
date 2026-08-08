# Investment Terminal — Architecture

## Status

**Document type:** High-level software architecture  
**Document status:** Canonical  
**Milestone:** Sprint 13 — Historical Comparison and Replay

## 1. Architectural Mission

Investment Terminal is a long-term personal investment intelligence platform optimized for correctness, determinism, traceability, reproducibility, explainability, historical integrity, maintainability, and explicit human decision ownership.

Canonical evidence lifecycle:

```text
Collect
→ Validate
→ Normalize
→ Analyse
→ Portfolio Intelligence
→ Decision Intelligence
→ Review Package
→ Immutable History
→ Structured History
→ Timeline
→ Comparison
→ Replay
→ Future Knowledge
→ AI-assisted human judgment
```

## 2. Architectural Style

Investment Terminal is a modular monolith with domain-oriented boundaries.

Rules:

- one deployable Python application;
- explicit domain models;
- application services orchestrate workflows;
- repositories own persistence queries;
- CLIs are thin entry points;
- immutable archive evidence is separate from rebuildable projections;
- no autonomous trading;
- no hidden recalculation inside History.

## 3. Core Domains

### Review Domain

Owns the versioned Review Package and assembles already-calculated domain outputs.

Review does not calculate indicators, portfolio values, recommendation rules, or historical comparisons.

### History Domain

Owns:

- `HistoricalSnapshot`;
- immutable archive writing;
- exact-byte preservation;
- SHA-256 verification;
- path confinement;
- append-only manifest;
- SQLite historical schema;
- schema migrations;
- explicit import state;
- structured import;
- timeline generation;
- History persistence repositories.

The History Domain stores and verifies historical facts.

### Historical Intelligence

**Status: Implemented foundation in Sprint 13.**

Owns relationships across historical facts:

- snapshot compatibility;
- portfolio-summary comparison;
- holdings comparison;
- recommendation comparison;
- deployment comparison;
- aggregate snapshot comparison;
- safe replay semantics.

Historical Intelligence does not mutate archive evidence and does not call market APIs.

### Future Knowledge Domain

Will derive reusable, versioned, traceable knowledge from verified historical evidence and comparison outputs.

Knowledge may be rebuilt. Historical evidence may not be rewritten.

## 4. History Persistence Architecture

```text
Review Package
      ↓
HistoricalSnapshotArchive
      ↓
Immutable JSON Archive
      ↓
HistoricalSnapshotManifest
      ↓
HistoricalManifestImportService
      ↓
HistoricalSQLiteStore
      ↓
Schema Migrator + Import State
      ↓
HistoricalImportPipeline
      ↓
Portfolio / Holdings / Recommendations / Deployment
      ↓
Timeline Events
```

Source-of-truth hierarchy:

```text
Archived JSON = canonical evidence
manifest.jsonl = append-only index
history.db = rebuildable projection
```

## 5. Schema Evolution

Sprint 13 introduced controlled SQLite migrations.

The current History schema target is **version 2**.

Migration requirements:

- sequential;
- transactional;
- idempotent;
- rejects unsupported future versions;
- preserves existing Sprint 12 databases.

Schema version 2 adds explicit snapshot import-state persistence.

## 6. Import-State Workflow

Canonical states:

```text
METADATA_ONLY
VERIFIED
IMPORTING
IMPORTED
FAILED
```

Import-state transitions are explicit and persisted. Detail import is atomic across:

```text
portfolio_summary
→ holdings
→ recommendations
→ deployment
→ timeline_events
```

A failed import cannot leave a misleading partial detail projection.

## 7. Historical Query Architecture

Repositories own SQL. Query services and CLIs consume typed results.

Implemented query boundaries include:

- chronological snapshot listing;
- package/date filters;
- latest snapshot;
- previous/next navigation;
- timeline by snapshot/type/subject/date/latest;
- explicit import-state access.

## 8. Historical Comparison Architecture

```text
Snapshot metadata
+ Import state
+ Comparison facts
        ↓
HistoricalSnapshotCompatibilityService
        ↓
PortfolioSummaryComparator
HoldingsComparator
RecommendationsComparator
DeploymentComparator
        ↓
HistoricalSnapshotComparisonService
        ↓
SnapshotComparison
```

Compatibility may be:

- `COMPATIBLE`;
- `PARTIALLY_COMPATIBLE`;
- `INCOMPATIBLE`.

`INCOMPATIBLE` short-circuits leaf comparisons. Soft warnings remain visible.

Comparators use persisted stable keys and never perform fuzzy identity matching.

## 9. Historical Replay Architecture

Supported modes:

```text
EXACT_ARCHIVED_PACKAGE
NORMALIZED_HISTORICAL_VIEW
```

Exact replay:

```text
HistoricalSnapshot
→ HistoricalReviewPackageLoader
→ verified exact archived payload
```

Normalized replay:

```text
HistoricalSnapshot
+ Import State
+ typed repositories
→ rebuildable normalized projection
```

`CURRENT_CODE_RECALCULATION` is intentionally unsupported. Replay does not access external data.

## 10. CLI Boundary

Current History CLIs:

```text
archive_review_package.py
import_history.py
query_history.py
compare_history.py
replay_history.py
```

CLI responsibilities:

```text
parse
→ resolve paths
→ construct dependencies
→ call service/repository boundary
→ format result
```

Forbidden:

- direct SQL;
- hidden migrations in read-only query CLIs;
- comparison business logic;
- replay business logic;
- historical recalculation.

## 11. Integrity Rules

Historical evidence must preserve:

- exact bytes;
- checksum identity;
- safe archive-root confinement;
- package schema identity;
- `generated_at` identity;
- append-only archive and manifest behavior;
- typed import state;
- atomic detail import;
- deterministic ordering.

## 12. End-to-End Verification

Sprint 13 includes a realistic deterministic fixture that validates:

```text
Review Package
→ Archive
→ Manifest
→ Migration
→ Metadata synchronization
→ Verified atomic import
→ Timeline
→ Query CLI
→ Comparison CLI
→ Exact replay
→ Normalized replay
```

No network access is required.

## 13. Dependency Rules

Allowed:

```text
CLI
→ Application Services / Repositories
→ Domain Models / Infrastructure
```

```text
Review
→ History
→ Historical Intelligence
→ Future Knowledge
```

Forbidden:

```text
History → Market API
History → current analysis calculation
Comparison → raw SQL
Replay → external data
CLI → domain-rule implementation
Knowledge → archive mutation
AI → canonical historical rewrite
```
