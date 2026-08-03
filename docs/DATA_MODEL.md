# Investment Terminal — Data Model

## Status

**Product:** Investment Terminal  
**Document type:** Canonical data-model specification  
**Document status:** Canonical  
**Updated after:** Sprint 12 — Historical Intelligence Foundation

This document defines the canonical data concepts of Investment Terminal, their responsibilities, relationships, validation rules, serialization requirements, persistence forms, and long-term evolution.

It covers:

- current portfolio models;
- review-package representations;
- historical snapshot identity;
- immutable archive metadata;
- append-only manifest records;
- SQLite historical tables;
- timeline-event records;
- future comparison and knowledge concepts.

`ARCHITECTURE.md` defines how domains interact. `CONSTITUTION.md` defines non-negotiable rules. This document defines what product data means.

---

# 1. Data-Model Philosophy

Investment Terminal uses explicit data models because financial and historical data must remain:

- understandable;
- validated;
- deterministic;
- reproducible;
- serializable;
- traceable;
- historically comparable;
- stable across product evolution.

A model exists only when it represents a meaningful product concept.

Examples:

| Model or Record | Product Question |
|---|---|
| `PortfolioHolding` | What instrument does the user own? |
| `CurrentPortfolio` | What does the user own now? |
| `PortfolioSnapshot` | How is the portfolio structured? |
| Review Package | What evidence did the system assemble for one review? |
| `HistoricalSnapshot` | What exact review artifact was preserved? |
| Manifest record | Where is that historical artifact and how is it identified? |
| `portfolio_summary` row | What was the normalized portfolio state for one snapshot? |
| `holdings` row | What historical position was recorded? |
| `recommendations` row | What machine recommendation existed at that time? |
| `deployment` row | What allocation or deployment action was proposed? |
| `timeline_events` row | What historical fact occurred and when? |
| Future knowledge entry | What pattern was derived from multiple verified snapshots? |

---

# 2. Canonical Model Rules

## 2.1 One Canonical Meaning

A business concept must not have multiple incompatible definitions.

Examples:

- one canonical portfolio holding;
- one canonical historical snapshot identity;
- one canonical archive checksum;
- one canonical package generation timestamp;
- one canonical snapshot metadata record.

Different serialized views are allowed only when they preserve meaning.

---

## 2.2 Domain Models and Serialized Forms

A Python model and its serialized form are different representations of the same concept.

```text
Canonical model
        ↓
Adapter or to_dict()
        ↓
JSON representation
        ↓
Review Package, manifest, or database import
```

Adapters may reshape fields for a consumer but must not silently change semantics.

---

## 2.3 Explicit State

Important states use explicit values.

Examples:

```text
READY
PARTIAL
STALE
MISSING
INVALID
CONNECTED
NOT_CONNECTED
COST_BASIS_ONLY
MARKET_VALUE_CONNECTED
ARCHIVED
```

`None` must not represent several unrelated states.

---

## 2.4 Immutability

Historical and calculated result models should be immutable where practical.

Preferred implementation:

```python
@dataclass(frozen=True, slots=True)
```

Historical evidence is immutable after successful preservation.

Corrections create new snapshots rather than mutating old ones.

---

## 2.5 Validation at Construction

Canonical models reject invalid state immediately.

Examples:

- invalid UUID;
- negative quantity;
- non-finite financial value;
- naive historical timestamp;
- archive time before generation time;
- unsafe relative path;
- malformed SHA-256 checksum;
- duplicate instrument key;
- duplicate snapshot path;
- inconsistent portfolio totals.

---

## 2.6 Time

Persistent timestamps use ISO 8601 and must be timezone-aware.

Example:

```text
2026-08-03T17:35:00+00:00
```

Distinct time concepts must remain separate:

- `generated_at`;
- `archived_at`;
- future `imported_at`;
- timeline `occurred_at`;
- quote timestamp;
- source timestamp.

---

## 2.7 Currency

Monetary data must carry or inherit explicit currency.

Current portfolio reporting commonly uses `EUR`.

Future multi-currency support must separate:

- instrument currency;
- quote currency;
- portfolio base currency;
- FX source;
- FX timestamp.

---

## 2.8 Exact Evidence vs Normalized Data

Historical data has two model categories:

### Canonical Evidence

Exact archived Review Package bytes.

### Normalized Projection

Selected structured fields imported into SQLite.

Normalized records support queries but do not replace original evidence.

---

# 3. Model Relationship Overview

```text
PortfolioPolicy
        │
        ▼
CurrentPortfolio
        │
        ├───────────────┐
        ▼               ▼
PortfolioSnapshot   PortfolioMarketValueResult
        │               │
        └───────┬───────┘
                ▼
       Review Package
                │
                ▼
       HistoricalSnapshot
                │
       ┌────────┴────────┐
       ▼                 ▼
Archived JSON      Manifest Record
       │                 │
       └────────┬────────┘
                ▼
         SQLite Snapshot
                │
    ┌───────────┼────────────┬──────────────┐
    ▼           ▼            ▼              ▼
Portfolio    Holdings   Recommendations   Deployment
 Summary
    └───────────┴────────────┴──────────────┘
                         │
                         ▼
                 Timeline Events
                         │
                         ▼
        Future Historical Intelligence
                         │
                         ▼
              Future Knowledge Entry
```

Not every relationship is a direct class dependency.

Many relationships are coordinated by application services.

---

# 4. Portfolio Domain

## 4.1 `PortfolioHolding`

**Status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/current_portfolio_models.py`

Represents one non-cash instrument owned by the user.

Core fields:

| Field | Type | Meaning |
|---|---|---|
| `symbol` | `str` | Internal symbol |
| `name` | `str` | Display name |
| `asset_type` | `str` | ETF, stock, bond, gold, other |
| `sleeve` | `str` | Strategic sleeve |
| `quantity` | `float` | Units owned |
| `average_cost` | `float` | Average acquisition cost |
| `currency` | `str` | Cost-basis currency |
| `isin` | `str | None` | International identifier |
| `exchange_ticker` | `str | None` | Market ticker |
| `strategy` | `str | None` | Holding strategy |

Stable instrument-key priority:

```text
ISIN
    else exchange_ticker
    else symbol
```

This key supports duplicate detection, quote matching, and historical identity.

---

## 4.2 `PortfolioPolicy`

**Status:** Implemented

Defines strategic target weights and portfolio base currency.

Core fields:

- core target weight;
- tactical target weight;
- cash target weight;
- monthly contribution;
- base currency.

Invariant:

```text
core + tactical + cash = 1.0
```

Weights refer to total portfolio value including cash.

---

## 4.3 `CurrentPortfolio`

**Status:** Implemented

Represents:

- portfolio identity;
- policy;
- holdings;
- cash balance.

Important invariants:

- holdings are validated canonical objects;
- instrument keys are unique;
- cash is finite and non-negative.

---

## 4.4 `PortfolioSnapshot`

**Status:** Implemented

Represents a structural portfolio state.

Core fields:

- portfolio name;
- base currency;
- total value;
- invested value;
- cash value;
- monthly contribution;
- asset breakdown;
- sleeve breakdown;
- strategy breakdown.

A snapshot must explicitly communicate whether values are cost-basis or market-value based.

---

# 5. Review Package Model

## 5.1 Review Package

**Status:** Implemented as a versioned JSON product artifact

The Review Package is the stable serialized handoff between:

- analysis domains;
- Portfolio Domain;
- Decision Domain;
- History Domain;
- AI interpretation.

Top-level identity fields include:

| Field | Meaning |
|---|---|
| `schema_version` | Review Package schema |
| `generated_at` | Time the review was generated |
| optional package metadata | Product and workflow identity |
| `sections` | Structured review sections |

Typical sections include:

- freshness;
- market analysis;
- stock analysis;
- opportunities;
- machine recommendations;
- portfolio;
- source-package evidence;
- warnings and limitations.

The Review Package is immutable once archived.

---

## 5.2 Portfolio Section

The historical import layer currently expects:

```text
sections.portfolio
```

Supported status values:

```text
COST_BASIS_ONLY
MARKET_VALUE_CONNECTED
```

### Cost-basis snapshot fields

Typical fields:

- `portfolio_name`;
- `base_currency`;
- `total_value`;
- `invested_value`;
- `cash_value`;
- `monthly_contribution`.

### Market-value fields

Typical fields:

- `portfolio_name`;
- `base_currency`;
- `invested_market_value`;
- `cash_value`;
- `total_market_value`;
- `positions`.

Market-value and cost-basis identity must agree on portfolio name and currency.

---

## 5.3 Machine Recommendations Section

Expected path:

```text
sections.machine_recommendations
```

Typical fields:

- `status`;
- `recommendations`;
- `allocation`.

Recommendation payloads may currently appear as:

- direct list;
- dictionary with `items`;
- dictionary with `recommendations`;
- dictionary with `candidates`.

Allocation payloads may appear as:

- direct list;
- `items`;
- `allocations`;
- `deployment`;
- `plan`;
- one allocation object.

The original payload is preserved in historical SQLite where practical.

---

# 6. Historical Snapshot Domain

## 6.1 `HistoricalSnapshot`

**Status:** Implemented  
**Canonical location:** `investment_terminal/history/historical_snapshot_models.py`

Represents the canonical metadata identity of one archived Review Package.

Fields:

| Field | Type | Meaning |
|---|---|---|
| `snapshot_id` | UUID string | Permanent snapshot identity |
| `package_id` | `str | None` | Optional Review Package identity |
| `package_schema_version` | `str` | Archived package schema |
| `product_version` | `str | None` | Investment Terminal version |
| `generated_at` | aware `datetime` | Package creation time |
| `archived_at` | aware `datetime` | Archive time |
| `relative_path` | `str` | Path inside history root |
| `checksum_sha256` | `str` | Exact archived-byte checksum |
| `supersedes` | UUID string or `None` | Explicit correction relation |
| `status` | `str` | Snapshot state |

Current status:

```text
ARCHIVED
```

---

## 6.2 `HistoricalSnapshot` Invariants

Required invariants:

- `snapshot_id` is a normalized UUID;
- `package_schema_version` is non-empty;
- `generated_at` is timezone-aware;
- `archived_at` is timezone-aware;
- `archived_at >= generated_at`;
- `relative_path` is relative and safe;
- `relative_path` identifies a JSON file;
- checksum is exactly 64 hexadecimal characters;
- `supersedes` is either absent or another UUID;
- a snapshot cannot supersede itself;
- status is explicit.

---

## 6.3 Serialization

A serialized snapshot record contains the same canonical fields.

Example:

```json
{
  "snapshot_id": "2f132e09-38c9-4471-bb48-875b4f9ec8e8",
  "package_id": "review-001",
  "package_schema_version": "1.0",
  "product_version": "0.12.0",
  "generated_at": "2026-08-03T17:35:00+00:00",
  "archived_at": "2026-08-03T17:36:00+00:00",
  "relative_path": "2026/08/review.json",
  "checksum_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "supersedes": null,
  "status": "ARCHIVED"
}
```

---

# 7. Immutable Archive Model

## 7.1 Archived Review Package

**Status:** Implemented

The archived package is not a new business model. It is the exact byte representation of a completed Review Package.

Properties:

- UTF-8 JSON;
- exact byte preservation;
- immutable file;
- checksum-identified;
- uniquely addressed by snapshot metadata;
- safe relative path below archive root.

Default layout:

```text
data/history/YYYY/MM/<snapshot-file>.json
```

---

## 7.2 Archive Source-of-Truth Rule

The archived JSON is canonical historical evidence.

It retains:

- fields not yet normalized;
- original recommendation detail;
- original allocation detail;
- future-compatible source material.

SQLite may be deleted and rebuilt.

The archive must not be rewritten.

---

# 8. Manifest Model

## 8.1 Manifest Record

**Status:** Implemented through `HistoricalSnapshotManifest`

Storage:

```text
data/history/manifest.jsonl
```

Each line is one serialized `HistoricalSnapshot`.

The manifest is:

- append-only;
- ordered by registration;
- human inspectable;
- duplicate protected;
- independent of SQLite.

---

## 8.2 Manifest Uniqueness

Current uniqueness constraints:

- unique `snapshot_id`;
- unique `relative_path`.

`package_id` is not necessarily unique because multiple historical snapshots may belong to the same logical package lineage.

---

## 8.3 Manifest Query Concepts

Supported query dimensions:

- snapshot ID;
- package ID;
- relative archive path;
- generated date range;
- latest snapshot.

The manifest is an index, not the evidence itself.

---

# 9. SQLite History Schema

## 9.1 Database Identity

Default path:

```text
data/history/history.db
```

Current schema version:

```text
1
```

Schema metadata is stored in:

```text
schema_metadata
```

SQLite uses:

- foreign keys;
- WAL mode;
- explicit indexes;
- idempotent initialization.

---

## 9.2 Entity Relationship Overview

```text
snapshots
   │
   ├── 0..1 portfolio_summary
   ├── 0..N holdings
   ├── 0..N recommendations
   ├── 0..N deployment
   └── 1..N timeline_events after timeline build
```

All detail records reference `snapshot_id`.

---

# 10. `schema_metadata`

Purpose:

- store database schema metadata;
- support future migrations.

Fields:

| Field | Type | Constraint |
|---|---|---|
| `key` | `TEXT` | Primary key |
| `value` | `TEXT` | Required |

Current record:

```text
key = schema_version
value = 1
```

---

# 11. `snapshots`

Purpose:

- normalized snapshot index;
- bridge between manifest and detail tables.

Fields:

| Field | Meaning |
|---|---|
| `snapshot_id` | Primary UUID |
| `package_id` | Optional package identity |
| `package_schema_version` | Review Package schema |
| `product_version` | Product version |
| `generated_at` | Package generation time |
| `archived_at` | Archive time |
| `relative_path` | Unique archive path |
| `checksum_sha256` | Exact byte checksum |
| `supersedes` | Optional snapshot FK |
| `status` | Snapshot status |
| `imported_at` | Reserved import-state timestamp |

Current indexes:

- generated time;
- package ID.

The SQLite row must represent the same metadata as the manifest record.

---

# 12. `portfolio_summary`

Purpose:

- one normalized portfolio summary per snapshot.

Cardinality:

```text
snapshots 1 → 0..1 portfolio_summary
```

Fields:

| Field | Meaning |
|---|---|
| `snapshot_id` | Primary and foreign key |
| `portfolio_name` | Portfolio identity |
| `base_currency` | Reporting currency |
| `total_value` | Total historical value |
| `invested_value` | Non-cash value |
| `cash_value` | Cash value |
| `monthly_contribution` | Contribution setting |
| `source_status` | Cost basis or market value |

Supported `source_status` values:

```text
COST_BASIS_ONLY
MARKET_VALUE_CONNECTED
```

Invariant:

```text
invested_value + cash_value ≈ total_value
```

Tolerance is limited to financial rounding.

---

# 13. `holdings`

Purpose:

- normalized historical portfolio positions.

Primary key:

```text
(snapshot_id, holding_key)
```

Fields:

| Field | Meaning |
|---|---|
| `snapshot_id` | Parent snapshot |
| `holding_key` | Stable historical position key |
| `symbol` | Normalized symbol |
| `name` | Display name |
| `asset_type` | Asset classification |
| `sleeve` | Portfolio sleeve |
| `strategy` | Optional strategy |
| `currency` | Position currency |
| `quantity` | Historical quantity |
| `unit_price` | Market price or average cost |
| `market_value` | Historical position value |
| `weight` | Share of total portfolio |

The column name `market_value` currently stores the imported historical value even for cost-basis-only records. The source interpretation comes from portfolio status and importer behavior.

A later schema version may rename this to a more neutral value field.

---

## 13.1 Holding Key Resolution

Current priority:

```text
instrument_key
    else ISIN
    else exchange_ticker
    else symbol
```

Keys must be unique within one snapshot.

The importer must not invent missing holdings.

If cost-basis detail is unavailable, zero holding rows are valid.

---

# 14. `recommendations`

Purpose:

- normalized machine recommendations for one snapshot.

Primary key:

```text
(snapshot_id, recommendation_key)
```

Fields:

| Field | Meaning |
|---|---|
| `snapshot_id` | Parent snapshot |
| `recommendation_key` | Stable row key |
| `symbol` | Optional instrument symbol |
| `action` | Normalized recommendation action |
| `score` | Optional numeric score |
| `confidence` | Optional confidence |
| `rationale` | Optional explanation |
| `payload_json` | Complete original recommendation object |

Current field aliases accepted by importer include:

### Symbol

```text
symbol
ticker
instrument
```

### Action

```text
recommendation
label
action
```

### Score

```text
score
ranking_score
total_score
```

### Confidence

```text
confidence
confidence_score
```

### Rationale

```text
rationale
reason
summary
thesis
```

Original payload preservation protects information not represented by normalized columns.

---

# 15. `deployment`

Purpose:

- normalized historical allocation or deployment records.

Primary key:

```text
(snapshot_id, deployment_key)
```

Fields:

| Field | Meaning |
|---|---|
| `snapshot_id` | Parent snapshot |
| `deployment_key` | Stable record key |
| `amount` | Optional monetary allocation |
| `share` | Optional allocation share |
| `reason` | Optional rationale |
| `payload_json` | Complete original source object |

Accepted amount aliases include:

```text
amount
allocation_amount
capital
value
```

Accepted share aliases include:

```text
share
weight
allocation_share
```

Invariant:

```text
0 <= share <= 1
```

Amounts must be finite and non-negative.

---

# 16. `timeline_events`

Purpose:

- represent chronological historical facts derived from normalized records.

Fields:

| Field | Meaning |
|---|---|
| `event_id` | Auto-increment primary key |
| `snapshot_id` | Parent snapshot |
| `event_type` | Event classification |
| `occurred_at` | Time of historical event |
| `subject_key` | Snapshot, portfolio, holding, recommendation, or deployment key |
| `payload_json` | Complete structured event payload |

Current event types:

```text
SNAPSHOT_ARCHIVED
PORTFOLIO_SUMMARY_RECORDED
HOLDING_RECORDED
RECOMMENDATION_RECORDED
DEPLOYMENT_RECORDED
```

Current timing semantics:

- `SNAPSHOT_ARCHIVED` uses `archived_at`;
- imported analytical facts use snapshot `generated_at`.

All persisted event timestamps are normalized to timezone-aware ISO 8601, generally UTC.

---

# 17. Historical Import Result Models

## 17.1 `ManifestImportResult`

**Status:** Implemented

Fields:

- `manifest_records`;
- `imported_records`;
- `skipped_records`.

Derived property:

```text
changed = imported_records > 0
```

Invariant:

```text
imported_records + skipped_records = manifest_records
```

All counts are non-negative integers.

---

## 17.2 `HistoricalImportResult`

**Status:** Implemented

Fields:

- `snapshot_id`;
- `holdings_imported`;
- `recommendations_imported`;
- `deployment_imported`;
- `timeline_events_created`.

Portfolio-summary import is currently implicit because exactly one summary is expected for a successful complete import.

A later version may expose an explicit summary count or import-state model.

---

# 18. Import-State Semantics

Current import completion is inferred from the presence of detail rows.

This is an implementation limitation.

Future recommended model:

```text
SnapshotImportState
```

Potential fields:

- snapshot ID;
- metadata synchronized at;
- package verified at;
- details imported at;
- timeline built at;
- import status;
- failure reason;
- importer version.

Possible statuses:

```text
METADATA_ONLY
VERIFIED
IMPORTING
IMPORTED
FAILED
```

This model should be introduced through an explicit schema migration.

---

# 19. Historical Identity Rules

## 19.1 Snapshot Identity

`snapshot_id` identifies one exact archived artifact.

It does not identify:

- a company;
- a portfolio;
- a package lineage;
- a review month.

---

## 19.2 Package Identity

`package_id` may identify a logical Review Package lineage or workflow-level artifact.

Multiple snapshots may share one package ID.

---

## 19.3 Instrument Identity

Historical instrument identity should prefer stable identifiers.

Priority:

```text
ISIN or canonical instrument key
    before exchange ticker
    before display symbol
```

Ticker-only identity may be ambiguous across exchanges and time.

---

## 19.4 Supersession

`supersedes` creates an explicit relation:

```text
new snapshot → prior snapshot
```

Supersession does not delete or invalidate prior evidence.

It records that a new snapshot is intended as a correction or replacement in interpretation.

---

# 20. Validation and Integrity Rules

Historical import must verify:

- safe archive path;
- file existence;
- checksum match;
- UTF-8;
- valid JSON;
- object top level;
- matching package schema;
- matching generated timestamp;
- registered snapshot metadata;
- duplicate protection;
- foreign-key consistency.

A checksum mismatch is a hard failure.

A valid JSON document with mismatched identity is also a hard failure.

---

# 21. Serialization Rules

Persistent JSON should use:

- UTF-8;
- explicit schema version;
- ISO 8601 timestamps;
- stable field names;
- no NaN or Infinity;
- deterministic ordering where used for normalized payload preservation.

Original payload JSON stored in SQLite should remain valid JSON.

---

# 22. Rebuildability Rules

The following data may be rebuilt:

- SQLite snapshot metadata;
- portfolio summaries;
- holdings;
- recommendations;
- deployment;
- timeline events;
- future historical comparisons;
- future knowledge projections.

Rebuild source:

```text
immutable archived JSON
        +
manifest metadata
```

The rebuild process must not invent missing facts.

---

# 23. Future Historical Intelligence Models

The following models are planned but not yet canonical implementations.

## 23.1 `SnapshotComparison`

Potential fields:

- earlier snapshot ID;
- later snapshot ID;
- comparison compatibility;
- portfolio-value change;
- holdings added;
- holdings removed;
- weight changes;
- recommendation transitions;
- deployment changes;
- warning changes.

---

## 23.2 `RecommendationTransition`

Potential fields:

- symbol;
- previous action;
- current action;
- previous score;
- current score;
- previous confidence;
- current confidence;
- duration;
- transition reason;
- supporting snapshot IDs.

---

## 23.3 `PortfolioEvolutionPoint`

Potential fields:

- snapshot ID;
- generated time;
- total value;
- invested value;
- cash value;
- sleeve weights;
- strategy weights;
- concentration;
- contribution context.

---

## 23.4 `HistoricalReplayRequest`

Potential fields:

- snapshot ID;
- replay mode;
- schema compatibility policy;
- requested output format;
- current-context inclusion flag.

Replay must distinguish exact historical evidence from calculations rerun with new code.

---

# 24. Future Knowledge Models

Knowledge models must be derived from verified history.

Potential concepts:

## 24.1 `EvidenceReference`

Fields may include:

- snapshot ID;
- event ID;
- subject key;
- source field;
- evidence type.

---

## 24.2 `KnowledgeEntry`

Potential fields:

- knowledge ID;
- statement;
- evidence references;
- sample size;
- confidence;
- valid context;
- calculation version;
- created time;
- superseded-by relation.

A Knowledge Entry must not exist without traceable evidence.

---

## 24.3 `ConfidenceResult`

Potential dimensions:

- source completeness;
- freshness;
- consistency;
- historical support;
- sample size;
- conflict level;
- model coverage.

Confidence must not be represented as one opaque number without explanation.

---

# 25. Schema Evolution Rules

Review Package schema and SQLite schema evolve independently.

Requirements:

1. Persistent schemas are versioned.
2. Archived packages remain readable.
3. Breaking changes require adapters or migration.
4. Existing field meanings must not silently change.
5. New timeline event types require documentation.
6. SQLite schema version 2 requires migration infrastructure.
7. Original archived payload remains available when normalized schemas evolve.

---

# 26. Data Ownership

| Data Concept | Owning Domain |
|---|---|
| Market quote | Market Data |
| Technical indicator | Technical Analysis |
| Fundamental metric | Fundamental Analysis |
| Portfolio holding | Portfolio |
| Recommendation | Recommendation / Decision |
| Review Package | Review |
| HistoricalSnapshot | History |
| Manifest record | History |
| SQLite history tables | History |
| Timeline event | History |
| Historical comparison | Future Historical Intelligence |
| KnowledgeEntry | Future Knowledge |

Ownership defines who validates and changes a concept.

---

# 27. Data-Model Anti-Patterns

Avoid:

- anonymous dictionaries passed through many layers;
- overloading `None`;
- ticker-only identity where stronger identifiers exist;
- storing naive timestamps;
- rewriting archived JSON;
- treating SQLite as canonical evidence;
- dropping original recommendation payloads without reason;
- silently converting invalid values to zero;
- inventing missing historical holdings;
- using one schema version for unrelated persistent formats;
- mutating previous history to represent correction;
- storing AI narrative as if it were deterministic fact.

---

# 28. Data-Model Review Checklist

Before adding a persistent model, ask:

- What exact product question does it answer?
- Which domain owns it?
- Is its identity stable?
- Are timestamps timezone-aware?
- Is currency explicit?
- Is invalid state rejected?
- Is serialization versioned?
- Is the model canonical evidence or a derived projection?
- Can it be rebuilt?
- Must the original payload be preserved?
- Does it require migration support?
- Can future comparison use it without reinterpretation?

---

# 29. Guiding Statement

> Investment Terminal must preserve the exact evidence first, normalize it second, compare it third, and derive knowledge only after every step remains traceable.

The data model should allow the system to explain:

- what it knew;
- when it knew it;
- which artifact preserved it;
- which structured records were derived;
- how later conclusions were formed.
