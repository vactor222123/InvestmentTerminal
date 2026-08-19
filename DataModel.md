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

`TaxLotSelection` records an explicit sale-to-acquisition quantity mapping;
no jurisdiction-specific FIFO, LIFO, or other disposal method is inferred.
`TaxLotAttributor` requires exact attribution of every SELL, prevents reuse of
acquisition quantity, validates time, instrument, and currency compatibility,
and produces deterministic lot-level realised evidence plus remaining open lots.

`UnrealizedPerformanceCalculator` values reconstructed open positions through
the existing explicit quote-provider boundary. Position results retain quote
source and timestamp, reject future or mismatched quotes, expose zero-cost
returns as unavailable, and aggregate only within a shared currency.

`PortfolioValuationSnapshot` combines compatible realised and point-in-time
unrealised projections while retaining both source projections. Currency rows
never mix unlike units. `PortfolioValuationHistory` requires immutable snapshot
identities and deterministic valuation-time ordering; it remains separate from
canonical Review History.

`PortfolioValuationHistoryRepository` defines append-only snapshot identity,
exact lookup, half-open time-window queries, recent/latest access, and immutable
history projection. Its in-memory implementation establishes executable
semantics without coupling to Review History.

`PortfolioValuationHistorySQLiteStore` schema version 1 binds one database to
immutable ledger and portfolio metadata. The SQLite repository stores canonical
strict JSON snapshots, rejects identity replacement, uses indexed deterministic
valuation-time queries, rolls back failed appends, and reconstructs the complete
domain projection after restart. Corrupt payloads fail visibly on read.

## Portfolio Risk Inputs

`ReturnObservation` records one finite total return over an explicit,
timezone-aware, non-overlapping period. `ReturnSeries` binds ordered unique
observations to a portfolio or instrument subject, currency, supported cadence,
and `RiskDataProvenance`. At least two observations are required so downstream
risk calculations never receive a singleton disguised as a series.

`PortfolioRiskInput` binds one portfolio series and deterministic unique
instrument series to a ledger, portfolio, and `as_of` cutoff. Future observation
or provenance timestamps fail closed. The contract performs no drawdown,
volatility, correlation, risk classification, or recommendation calculation.

`PortfolioDrawdownCalculator` compounds the validated portfolio returns into a
deterministic wealth path. Each `PortfolioDrawdownPoint` preserves its running
peak and exact relative decline. `PortfolioDrawdownAnalysis` records the earliest
maximum peak/trough episode and its first recovery, when present, while retaining
portfolio identity, currency, cadence, cutoff, and source provenance. It does
not assign qualitative risk labels or recommendations.

`PortfolioVolatilityCalculator` calculates the arithmetic mean and sample
standard deviation of validated portfolio returns. Annualisation uses an
explicit positive `periods_per_year` input rather than inferring a market
calendar. `PortfolioVolatilityAnalysis` preserves the observation count,
currency, cadence, source provenance, periodic volatility, and annualised
volatility without assigning risk labels or thresholds.

`PortfolioCorrelationCalculator` calculates pairwise Pearson correlation for
the portfolio and instrument return series using only exact shared observation
periods. `PortfolioCorrelationPair` keeps both source provenances and exposes
currency mismatch, cadence mismatch, insufficient overlap, and zero variance
as explicit unavailable evidence. Correlation remains descriptive and does not
imply causation, classification, or a recommendation.

`PortfolioRebalancingEvidenceBuilder` converts canonical strategic policy gaps
into bucket-level `INCREASE`, `REDUCE`, or `HOLD` evidence using an explicit
caller-supplied tolerance. It exposes the proposed adjustment amounts and the
portion that can be funded by opposing reductions, while explicitly denying
execution authority. Instrument selection and trade execution remain outside
this contract.

`PortfolioStrategyRuleSet` is a versioned, effective-dated configuration for
`CORE_LONG_TERM`, `STOCK_LONG_TERM`, `POSITION_TRADE`, and `CASH_RESERVE` in
canonical order. Each strategy has its own explicit review cadence and ordered
measurable `StrategyRuleCondition` records, including phase, comparison,
threshold, unit, and missing-data action. The contract supplies no hidden
investment thresholds, performs no evaluation, and grants no execution authority.

`PortfolioStrategyRuleEvaluator` compares explicit strategy metric evidence with
the effective versioned rule set. Every condition result preserves its observed
value, evidence identity, comparison, and reason. Missing metrics follow the
configured `FAIL` or `REVIEW` action, unit mismatches fail closed, and aggregate
status never grants execution authority.

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

## External Context Evidence

The Context domain owns provider-independent immutable contracts for `NEWS`,
`MACROECONOMIC`, `GEOPOLITICAL`, and `EVENT` records. Each
`ExternalContextRecord` preserves normalized subjects, an optional event time,
and an explicit uncertainty level with reasons whenever uncertainty is not
`NONE`.

`ExternalContextProvenance` records the provider, provider record identity,
publication and fetch timestamps, and optional source URL and SHA-256 checksum.
`ExternalContextQualityService` evaluates caller-configured freshness in hours
and reports `READY`, `PARTIAL`, or `STALE` without hiding incomplete lineage.
`ExternalContextEvidence` binds the normalized record, provenance, and quality
assessment. Provider ingestion, persistence, sentiment calculation, Review
Package composition, and AI interpretation remain separate later boundaries.

`ExternalContextQuery` defines an explicit half-open publication window,
requested context types and subjects, freshness policy, and result limit.
Provider adapters implement `ExternalContextProvider` and return normalized
`ExternalContextSourceItem` values rather than leaking provider payloads into
the domain. `ExternalContextIngestionService` rejects out-of-scope, future,
duplicate, oversized, or malformed provider results, applies the Package 1
quality policy, and returns deterministic `ExternalContextIngestionResult`
evidence. It does not persist records or interpret their investment meaning.

`ExternalContextRepository` defines append-only identity semantics and
deterministic publication-time and subject queries. Its in-memory reference
implementation rejects reuse of either canonical context identity or provider
source identity. Durable SQLite storage remains a separate adapter boundary.

`ExternalContextSQLiteStore` and `SQLiteExternalContextRepository` provide
schema-versioned durable storage, atomic append, indexed time/subject queries,
strict JSON round-trips, and restart-safe reconstruction.

`ExternalContextReviewAdapter` projects normalized evidence into the Review
Package without moving interpretation authority upstream. It preserves record,
provenance, quality, freshness, and uncertainty, applies deterministic ordering,
and exposes explicit aggregate and empty-evidence states.

`ExternalContextSentimentEvidence` attaches a provider-independent, traceable
sentiment assessment to one canonical context identity. Labels, optional bounded
score/confidence, assessment time, method/version, and reasons remain explicit;
the Review projection accounts for assessed and unassessed records without
inventing sentiment for missing evidence.

## Market Discovery

`MaintainedAssetUniverse` is an immutable, versioned, effective-dated snapshot
of canonical `InstrumentIdentity` members. `AssetUniverseMember` records when
an instrument entered the maintained snapshot and may preserve an explicit
inclusion reason. Members are unique by the strongest canonical instrument key
and serialize in deterministic key order.

`MaintainedAssetUniverseEvidence` binds the snapshot to existing market-metadata
source provenance and explicit `READY`, `PARTIAL`, or `STALE` quality. Provider
ingestion, persistence, sector classification, screening, ranking, and Review
composition remain separate later boundaries. The legacy text-file
`InvestmentUniverse` remains a backward-compatible local symbol-list input.

`MaintainedAssetUniverseQuery` defines requested universe identities, a bounded
half-open observation window, freshness policy, and result limit. Provider
adapters return normalized `MaintainedAssetUniverseSourceItem` values.
`MaintainedAssetUniverseIngestionService` rejects out-of-scope, future,
duplicate, oversized, or malformed provider results, applies the established
market-metadata quality policy, and returns deterministic evidence without
persisting or screening it.

`MaintainedAssetUniverseRepository` defines append-only canonical universe and
provider-source identity semantics. It supports exact lookup, half-open
observation-time queries, version history per universe, canonical instrument
membership queries, and latest-snapshot access. The in-memory reference
implementation establishes deterministic behavior before durable persistence;
screening, ranking, and Review composition remain outside this boundary.

`MaintainedAssetUniverseSQLiteStore` and
`SQLiteMaintainedAssetUniverseRepository` provide schema-versioned durable
storage, atomic append, strict JSON round-trips, indexed temporal, universe, and
instrument queries, rollback on failure, and restart-safe reconstruction.
Corrupt payloads fail visibly rather than being replaced or skipped.

`ETFDiscoveryEvidenceBuilder` projects ETF members from one maintained universe
and joins the existing `ETFCharacteristicsEvidence` and
`ETFCompositionEvidence` contracts by canonical instrument identity. Every ETF
member remains visible when either evidence section is absent, with explicit
missing-evidence accounting and deterministic `READY`, `PARTIAL`, or `STALE`
status. Conflicting, duplicate, future, or out-of-universe evidence fails
closed. Discovery assembly performs no scoring, ranking, recommendation, or
trade selection.

`SectorAnalysisEvidenceBuilder` joins existing `CompanyClassification` values
to STOCK members of one maintained universe. It reports deterministic sector
and industry counts, eligible/classified coverage, and canonical identities for
unclassified instruments. ETF members are outside this company-classification
projection. Duplicate, ambiguous exchange-scoped symbols and out-of-universe
classifications fail closed. Sector evidence remains descriptive and grants no
scoring, ranking, recommendation, or trading authority.

`ScreeningPolicy` contains versioned, effective-dated, caller-owned criteria
with explicit operators, thresholds, units, and missing-data actions.
`ScreeningPipeline` evaluates metric evidence for every maintained-universe
member using indexed joins suitable for broad universes. Results preserve
criterion-level evidence identifiers and distinguish `PASS`, `FAIL`, and
`REVIEW`; missing values and unit mismatches remain visible. Screening output
does not rank candidates, recommend investments, or authorize execution.

## Integrated Investment Review Workflow

`WorkflowArtifactIdentity` identifies a stage artifact by normalized type and
stable caller-owned identity without embedding or mutating the artifact.

`InvestmentReviewWorkflowStageResult` records one canonical stage as
`COMPLETED`, `SKIPPED`, or `FAILED`. It preserves the exact dependency contract,
timezone-aware start/completion boundaries, immutable artifact identities,
warnings, and status-specific failure or skip reasons.

`InvestmentReviewWorkflowRun` is the versioned, immutable report for one full
workflow attempt. It requires every stage in canonical order, verifies that
executed stages have completed dependencies, keeps every stage inside the run
time boundary, and serializes without changing the Review Package contract.

`IntegratedInvestmentReviewEvidence` is the typed pre-generation aggregate. It
requires a current `PortfolioSnapshot` and ready canonical current-state market
result, and may carry ordered external context/sentiment plus ETF discovery,
sector analysis, and screening evidence. Optional omissions are represented by
deterministic `missing_evidence`; discovery inputs must share one maintained
universe identity, and no source timestamp may exceed `assembled_at`.

`IntegratedReviewPackageExportResult` binds one generated
`InvestmentReviewPackage` to its atomically replaced output path. The package
retains Review schema version `1.0`; integrated provenance and Phase 5 evidence
are projected inside existing sections rather than creating a competing Review
contract.

`IntegratedReviewHistoryResult` binds a registered `HistoricalSnapshot` to the
separate manifest-metadata and detail-import results that created its
rebuildable SQLite projection. `HistoricalProjectionAfterArchiveError` carries
the registered snapshot and a `FAILED` projection outcome when either
projection step fails, preserving canonical archive success without reporting
the overall operation as complete.

`IntegratedReviewComparisonResult` is the typed historical comparison-stage
outcome. `COMPLETED` binds the current snapshot, selected previous snapshot,
and a non-incompatible `SnapshotComparison`; `FIRST_RUN` records that no
earlier snapshot exists; `UNAVAILABLE` records absent current import state or
the lack of an earlier compatible imported projection. Non-completed outcomes
carry a reason and no fabricated comparison artifact.

The `review` command persists `InvestmentReviewWorkflowRun.to_dict()` as the
workflow report and uses `WorkflowArtifactIdentity` values for the exported
Review Package, registered snapshot, History projection, and optional
comparison. A first-run comparison remains a completed read-only stage with an
explicit warning and no comparison artifact.

`WorkflowExecution` couples the complete `InvestmentReviewWorkflowRun` with an
optional operational error for the CLI boundary. The normalized error reason
belongs to the failed stage, later stages carry skip reasons, and the error is
raised to the user only after the canonical report is durably written.

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

## Operational Data Baseline

`OperationalDataBaseline` is the versioned, immutable Phase 7 operational
inventory. It contains:

```text
schema_version
generated_at
providers[]
stores[]
refresh_observability
measured_performance
authority
```

Provider entries expose only identity, roles, `CONFIGURED` or `UNCONFIGURED`,
and the configuration source name. Credential values are never serialized.

Store entries preserve configured path, `READY`/`ABSENT`/`ERROR` state, known
schema version, measured count, deterministic coverage records, and a visible
error when inspection fails. Candle coverage is grouped by symbol, resolution,
and currency. Maintained-universe coverage preserves snapshot identity,
observation time, member count, and asset-type counts. Portfolio, transaction,
valuation, context, workflow, and backup inputs expose aggregate presence and
ranges without record contents.

`UNMEASURED` is not zero, absent, stale, or failed. The baseline does not claim
freshness, approximately 20-year candle coverage, approximately 1000-company
universe coverage, analytical meaning, or execution authority.

## Yahoo Candle Qualification Result

`YahooCandleQualificationResult` is immutable and schema-versioned. It records:

```text
provider_identity = YAHOO_FINANCE
status = SUCCESS | EMPTY | FAILED
request(symbol, resolution, currency, requested_start, requested_end)
started_at / completed_at / duration_seconds
coverage(candle_count, earliest_candle_at, latest_candle_at)
failure(type, reason)
limitations[]
```

`SUCCESS` requires positive ordered in-window coverage. `EMPTY` requires an
explicit zero count. `FAILED` preserves unknown coverage and normalized visible
failure details. Returned candles must exactly match the requested identity,
currency, resolution, and half-open window and must be unique and ordered.

The result is operational provider evidence only. It is not canonical market
history, analytical evidence, investment interpretation, or trading authority.
