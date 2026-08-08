# Investment Terminal — Data Model

## Status

**Document type:** Canonical data-model specification  
**Updated after:** Sprint 13 — Historical Comparison and Replay

## 1. Data Philosophy

Financial and historical data must remain explicit, validated, deterministic, serializable, traceable, and comparable.

Canonical historical evidence and rebuildable normalized projections are separate concepts.

## 2. Historical Source-of-Truth Model

```text
Archived Review Package
    canonical exact evidence

HistoricalSnapshot
    canonical metadata identity

manifest.jsonl
    append-only snapshot index

history.db
    rebuildable normalized projection
```

## 3. `HistoricalSnapshot`

Implemented immutable metadata model.

Core fields:

| Field | Meaning |
|---|---|
| `snapshot_id` | normalized UUID |
| `package_id` | optional package identity |
| `package_schema_version` | Review Package schema |
| `product_version` | producing product version |
| `generated_at` | aware package-generation time |
| `archived_at` | aware archive time |
| `relative_path` | safe path under History root |
| `checksum_sha256` | SHA-256 of exact archived bytes |
| `supersedes` | optional correction lineage |
| `status` | explicit snapshot state |

Current snapshot status:

```text
ARCHIVED
```

## 4. History SQLite Schema

Current schema target:

```text
2
```

Schema metadata is stored in `schema_metadata`.

Primary tables:

```text
snapshots
snapshot_import_state
portfolio_summary
holdings
recommendations
deployment
timeline_events
```

Relationships:

```text
snapshots
 ├─ 0..1 snapshot_import_state
 ├─ 0..1 portfolio_summary
 ├─ 0..N holdings
 ├─ 0..N recommendations
 ├─ 0..N deployment
 └─ 0..N timeline_events
```

## 5. `HistoricalImportState`

Implemented explicit workflow model.

Statuses:

```text
METADATA_ONLY
VERIFIED
IMPORTING
IMPORTED
FAILED
```

Core fields include:

- snapshot ID;
- metadata synchronized at;
- package verified at;
- details imported at;
- timeline built at;
- importer version;
- failure reason;
- updated at.

The model replaces inference from “detail rows exist”.

## 6. Normalized Historical Read Models

Implemented typed projections:

### `HistoricalPortfolioSummary`

- portfolio identity;
- base currency;
- total value;
- invested value;
- cash value;
- monthly contribution;
- source status;
- derived invested/cash weights.

### `HistoricalHolding`

- stable `holding_key`;
- symbol/name;
- asset type;
- sleeve/strategy;
- currency;
- quantity;
- unit price;
- market value;
- weight.

### `HistoricalRecommendation`

- stable `recommendation_key`;
- symbol/action;
- optional score/confidence/rationale;
- immutable original JSON payload.

### `HistoricalDeployment`

- stable `deployment_key`;
- optional amount/share/reason;
- immutable original JSON payload.

## 7. Timeline Event Model

`HistoricalTimelineEvent` is the canonical typed event result for History queries.

Timeline events preserve:

- event type;
- snapshot identity;
- occurrence time;
- optional subject key;
- structured payload.

Timeline ordering is deterministic.

## 8. Comparison Models

Implemented comparison models include:

- `ScalarChange`;
- `PortfolioSummaryChange`;
- `HoldingChange`;
- `RecommendationChange`;
- `DeploymentChange`;
- `SnapshotComparison`.

Change categories for keyed collections:

```text
ADDED
REMOVED
CHANGED
UNCHANGED
```

Stable persisted keys define identity. Different keys are never fuzzy-matched.

## 9. Comparison Facts

`HistoricalComparisonFacts` is a minimal typed projection used only for compatibility assessment.

It contains:

- portfolio-summary presence;
- portfolio name;
- base currency;
- source status;
- row counts for detail/timeline projections.

It does not calculate deltas.

## 10. Snapshot Compatibility Result

Compatibility states:

```text
COMPATIBLE
PARTIALLY_COMPATIBLE
INCOMPATIBLE
```

Hard incompatibilities include:

- invalid chronology;
- unsupported package schema;
- portfolio identity mismatch;
- base-currency mismatch.

Soft warnings include:

- source-status changes;
- missing structured details;
- non-`IMPORTED` state.

## 11. Replay Models

`HistoricalReplayRequest` defines:

```text
EXACT_ARCHIVED_PACKAGE
NORMALIZED_HISTORICAL_VIEW
CURRENT_CODE_RECALCULATION
```

Sprint 13 supported modes:

```text
EXACT_ARCHIVED_PACKAGE
NORMALIZED_HISTORICAL_VIEW
```

`CURRENT_CODE_RECALCULATION` is defined but unsupported.

`HistoricalReplayResult` includes:

- snapshot ID;
- mode;
- package schema version;
- archive evidence SHA-256;
- immutable payload;
- warnings.

## 12. Evidence vs Projection Semantics

Exact replay returns verified archive payload.

Normalized replay returns typed SQLite data:

```text
snapshot
import_state
portfolio_summary
holdings
recommendations
deployment
timeline_events
```

Normalized replay must identify itself as a rebuildable projection.

## 13. Time and Currency

Persistent timestamps are timezone-aware ISO-8601.

Distinct time concepts remain separate:

- generated;
- archived;
- synchronized;
- verified;
- imported;
- timeline occurrence;
- updated.

Currency identity must be explicit. Historical comparison rejects base-currency mismatch.

## 14. Immutability

Historical result models should use immutable data structures where practical.

Corrections create new snapshots. Existing archived evidence is never rewritten.
