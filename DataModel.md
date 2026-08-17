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

## Multi-Asset Market Metadata

Provider-independent immutable contracts define:

- `InstrumentIdentity` for security identity and exchange-scoped tickers;
- `CurrencyMetadata` for explicit currency codes and minor units;
- `TradingCalendarMetadata` for versioned timezone/source provenance;
- `ExchangeMetadata` for exchange, country, calendar, and supported currencies.

An ISIN remains the strongest instrument key. Without an ISIN, an exchange
code scopes an exchange ticker as `EXCHANGE:TICKER`. Calendar metadata records
identity and provenance only; session calculation remains in the owning
freshness or History service.

Every acquired market-metadata record may carry `MarketMetadataProvenance`
with source, source-record identity, observation/fetch timestamps, and an
optional SHA-256 checksum. `MarketMetadataQualityAssessment` exposes
`READY`, `PARTIAL`, or `STALE` explicitly from configured freshness and
lineage completeness; it does not convert incomplete evidence into a
complete-looking result.

ETF reference evidence uses `ETFCharacteristics` for provider-independent
facts linked to an ETF `InstrumentIdentity`. Unavailable characteristics are
listed explicitly in `missing_characteristics`. `ETFCharacteristicsEvidence`
binds those facts to source provenance and its explicit quality assessment;
it does not infer missing fund data.

`ETFComposition` represents reported constituent holdings and categorical
exposures without assuming that a provider supplied the whole fund. Holdings
may carry an `InstrumentIdentity` when one is available; otherwise their
normalized name remains explicit. Decimal weights are bounded, duplicates are
rejected, and coverage is reported separately for holdings and each exposure
dimension. `ETFCompositionEvidence` attaches source provenance and quality
without changing portfolio or Review contracts.

## Portfolio Transaction Ledger

The Portfolio domain owns immutable lifecycle transactions independently from
current holding snapshots and Review History. `PortfolioTransaction` represents
`BUY`, `SELL`, `DIVIDEND`, and `FEE` events with timezone-aware occurrence,
explicit settlement currency, stable identity, and type-specific monetary
fields. `PortfolioTransactionLedger` requires unique transaction identities and
deterministic chronological ordering. Persistence, lot matching, performance,
and position reconstruction remain separate later boundaries.

`PortfolioTransactionRepository` defines append-only identity semantics,
exact lookup, half-open time-window queries, instrument queries, and immutable
ledger projection without exposing storage details. Its in-memory reference
implementation establishes deterministic behavior before a durable adapter is
introduced.

`PortfolioTransactionSQLiteStore` owns schema version 1, immutable ledger
metadata, and single-operation rollback. `SQLitePortfolioTransactionRepository`
stores canonical strict JSON payloads with indexed occurrence and instrument
keys, preserving the repository contract across process restarts.

`TransactionImportBatch` and `TransactionImportResult` preserve source and
import time while accounting separately for every imported and duplicate input
identity. Re-import is idempotent without silently removing duplicate evidence.

`PortfolioTransactionCsvParser` is the provider-neutral UTF-8 ingestion
boundary. It validates one explicit canonical schema, preserves source order and
duplicate rows, constructs canonical instrument identities, and reports invalid
domain values with their CSV line number before producing an import batch.

`PositionReconstructor` deterministically projects the ordered ledger into open
positions using average-cost accounting. It preserves canonical instrument
identity and cost currency, ignores non-trade cash events, removes fully sold
positions, and fails closed when a sale exceeds the available quantity.

`RealizedPerformanceCalculator` applies the same average-cost accounting to
each SELL event and preserves sale proceeds, allocated cost basis, gain/loss,
and return percentage. Aggregates remain separated and deterministically
ordered by currency, so values in unlike currencies are never silently mixed.

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
