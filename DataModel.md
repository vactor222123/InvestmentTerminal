# Investment Terminal — Data Model

**Status:** Canonical data-boundary summary  
**Current baseline:** Sprint 30 closure

## Principle

Investment Terminal does not have one universal SQLite source of truth.
Authority depends on the domain.

```text
History:
archived Review Package bytes = canonical evidence
history.db = rebuildable projection

Knowledge:
versioned Knowledge records = canonical Knowledge boundary

Provider accounting:
provider usage/cost ledger = operational accounting only

Grounded generations:
grounded generation store = persisted generated evidence only
```

## History

Historical archive records preserve exact Review Package bytes and checksums.
The manifest is append-only navigation metadata. SQLite History tables are
rebuildable structured projections used for query, comparison, and replay.

Important concepts include:

- HistoricalSnapshot;
- import state;
- timeline event;
- snapshot comparison;
- replay result.

## Knowledge

A Knowledge record is immutable/versioned and contains:

```text
knowledge_id
knowledge_type
version
subject_key
statement
valid_from
valid_to
generated_at
status
evidence[]
```

Evidence references preserve:

```text
evidence_type
evidence_id
observed_at
checksum_sha256
```

Knowledge identity is stable across persistence and envelope projection.

## Provider Usage/Cost Ledger

Operational provider accounting records include request identity, provider/model
identity, token usage, currency, exact Decimal costs, and recorded timestamp.

The ledger is immutable by request identity and supports:

- exact lookup;
- deterministic list;
- bounded recent query;
- half-open time-window query;
- exact summary aggregation.

It is not canonical investment evidence.

## Persisted Grounded Generations

`PersistedGroundedGeneration` is the durable projection of one ADMISSIBLE
grounded generation.

Fields:

```text
request_id
generated_at
prompt_protocol_identity
answer_protocol_identity
provider_identity
model_identity
selected_knowledge_identities
cited_knowledge_identities
generation
trace
```

Invariants:

- request identity is immutable;
- timestamps are timezone-aware;
- citations are a subset of selected Knowledge identities;
- generation prompt request identity matches the persisted request identity;
- trace request identity matches;
- trace validation status must be `ADMISSIBLE`.

SQLite schema version 1 stores one row per request identity and deterministic
JSON projections for selected/cited identities, generation, and trace.

Repository queries:

```text
get / require
list_all
list_recent(limit)
list_between(started_at, ended_at)
```

`list_between` uses half-open semantics:

```text
[started_at, ended_at)
```

## Authority Relationships

```text
History evidence
→ explicit ingestion
→ Knowledge evidence-backed statements
→ grounded generation inputs
→ generated evidence
```

Persisted generations do not modify the Knowledge records they cite.

## Data Integrity Rules

- no silent overwrite of immutable request/version identities;
- no naive datetimes in persisted temporal boundaries;
- deterministic ordering for list/query outputs;
- explicit schema versions for operational SQLite stores;
- corrupt or unsupported runtime stores fail readiness closed;
- archived History bytes are never rewritten.
