# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 19 — Knowledge Domain Foundation
implementation complete; final repository verification pending
```

## Completed foundation

### Sprint 12–18

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, research provenance/population quality, and explicit archive continuity are complete.

### Sprint 19 — Knowledge Domain Foundation

Delivered:

```text
KnowledgeEvidenceReference
KnowledgeRecord
KnowledgeEvidenceProvenanceService
KnowledgeProvenanceAssessment
KnowledgeRecordRepository
InMemoryKnowledgeRecordRepository
KnowledgeSQLiteStore
SQLiteKnowledgeRecordRepository
HistoricalSnapshotKnowledgeSource
HistoricalSnapshotKnowledgeProjectionService
KnowledgeRecordEnvelope
KnowledgeRecordEnvelopeService
KnowledgeQueryService
KnowledgeTemporalComparison
KnowledgeTemporalComparisonService
read-only Knowledge CLI
real Knowledge SQLite E2E
```

## Knowledge Domain Boundary

Knowledge is a downstream, rebuildable, evidence-grounded domain. It does not import or mutate the History package.

Canonical dependency direction:

```text
History / verified evidence
        ↓
CLI or application composition
        ↓
neutral Knowledge source contract
        ↓
Knowledge projection
        ↓
KnowledgeRecord
        ↓
Knowledge repository/query/provenance
```

`investment_terminal.knowledge` must not import `investment_terminal.history`.

## Canonical Knowledge Record

A Knowledge record is immutable and versioned:

```text
knowledge_id
knowledge_type
version
subject_key
statement
valid_from
valid_to
generated_at
evidence
status
```

Supported v1 knowledge types:

```text
FACT
RELATIONSHIP
PATTERN
```

Supported statuses:

```text
ACTIVE
SUPERSEDED
```

Knowledge v1 does not encode predictive confidence, success probability, recommendation effectiveness, causal claims, or AI-generated authority.

## Evidence and Provenance

Canonical snapshot-backed evidence carries:

```text
evidence_type = HISTORICAL_SNAPSHOT
evidence_id = exact snapshot UUID
observed_at = exact source timestamp
checksum_sha256 = exact archive checksum
```

Derived evidence references may be rebuildable and therefore need not be checksum-backed.

Knowledge provenance statuses:

```text
COMPLETE
PARTIAL
```

`COMPLETE` means at least one checksum-backed canonical historical snapshot is present in lineage. It does not mean the statement is predictive, causal, representative, or investment-effective.

Evidence timestamps may not be later than `KnowledgeRecord.generated_at`.

## Persistence

Knowledge has its own SQLite boundary and does not alter History schema.

```text
Knowledge schema version = 1
knowledge_schema_metadata
knowledge_records
knowledge_evidence
```

Primary record identity:

```text
(knowledge_id, version)
```

Record and evidence insertions are transactional.

History schema remains version 2 and separate from Knowledge persistence.

## Query Contract

Canonical repository/query operations:

```text
get
require
list_all
find_by_subject
find_valid_at
latest_for_subject
```

Ordering and temporal validity are deterministic. `find_valid_at` uses inclusive validity boundaries.

Query results are exposed as:

```text
KnowledgeRecordEnvelope
├── KnowledgeRecord
└── KnowledgeProvenanceAssessment
```

Provenance is derived on demand and is not duplicated in SQLite.

## Temporal Comparison

Knowledge temporal comparison is descriptive only and reports:

```text
statement_changed
status_changed
validity_changed
evidence_added
evidence_removed
evidence_changed
any_change
```

It requires two different versions of the same `knowledge_id` and orders them deterministically by `generated_at`, then `version`.

It does not score whether a change is better, worse, successful, predictive, or effective.

## Read-only CLI

Knowledge CLI commands:

```text
list
show
subject
valid
latest
compare
```

The CLI composes `KnowledgeSQLiteStore`, `SQLiteKnowledgeRecordRepository`, `KnowledgeQueryService`, and `KnowledgeTemporalComparisonService`. It owns no independent SQL/query semantics.

Both human and JSON output expose provenance and descriptive temporal changes.

## Stable Guardrails

Sprint 19 preserves these boundaries:

- Knowledge does not import History;
- History remains canonical historical evidence;
- Knowledge is rebuildable/versioned;
- snapshot evidence identity and checksum remain traceable;
- no network I/O in pure Knowledge calculation;
- no prediction or recommendation-effectiveness semantics;
- no causal inference;
- no success/failure or win-rate semantics;
- no hidden AI authority field;
- no mutation of History from Knowledge;
- CLI remains read-only composition/rendering.

## E2E Coverage

Sprint 19 covers:

```text
neutral snapshot evidence input
→ deterministic Knowledge projection
→ provenance validation
→ Knowledge SQLite persistence
→ deterministic repository/query service
→ provenance envelope
→ temporal comparison
→ JSON/human CLI
```

The E2E also verifies that Knowledge persistence does not create or modify a History database.

## Testing Status

Focused Sprint 19 tests are implemented.

Final closure requires:

```text
python -m pytest -q
```

to pass after applying this package.

## Deferred Capabilities

Still deferred:

- automatic History-to-Knowledge ingestion workflow;
- projection from snapshot comparison/replay/outcome research;
- knowledge deduplication across semantically equivalent statements;
- relationship graph traversal;
- richer temporal conflict/supersession rules;
- Knowledge schema migration beyond v1;
- natural-language retrieval/ranking;
- embeddings/vector search;
- LLM-generated Knowledge records;
- predictive confidence;
- recommendation effectiveness;
- causal inference;
- autonomous trading or broker execution.

## Next Decision

Sprint 19 establishes the deterministic Knowledge Domain foundation required before any evidence-grounded AI experience.

A future AI milestone must consume traceable Knowledge records and provenance without turning derived statements into unqualified authority or introducing unsupported predictive/causal semantics.
