# Investment Terminal — Software Architecture

**Status:** Canonical architecture  
**Current baseline:** Sprint 30 closure

## Architectural Style

Investment Terminal is a modular monolith with explicit domain and application
boundaries. Infrastructure adapters are composed at CLI/server roots and must
not leak persistence or provider details into domain models.

## Authority Model

```text
Deterministic current-state analysis
→ Review Package
→ History
→ explicit verified ingestion
→ Knowledge
→ grounded generation
→ validated generated evidence
```

Authority does not flow backwards.

- History is canonical historical evidence.
- Knowledge is explicit, versioned, evidence-backed derived knowledge.
- Grounded AI consumes Knowledge.
- Persisted grounded generations are generated evidence only.
- Provider usage/cost data is parallel operational accounting.

No AI output becomes History or Knowledge automatically.

## Major Domains

- Market Data
- Technical Analysis
- Fundamental Analysis
- Ranking
- Recommendation
- Portfolio
- Decision
- Review
- History
- Historical Intelligence
- Knowledge
- Evidence-Grounded AI
- Provider Operations
- Server Runtime

## History Boundary

Canonical historical evidence is the immutable archived Review Package.

```text
archived package bytes
→ integrity verification
→ manifest navigation
→ rebuildable SQLite projection
→ comparison / replay / query
```

History SQLite is a projection, not the source of truth.

## Knowledge Boundary

Knowledge records are immutable/versioned and contain explicit evidence
references. History-to-Knowledge ingestion is explicit, verified, deterministic,
idempotent, and dry-run capable.

Knowledge may be queried by application services, but non-History modules must
not reach into History internals to reconstruct historical authority.

## Grounded AI Boundary

```text
Knowledge envelopes
→ context selection
→ GroundedPromptInput
→ provider adapter
→ strict parsing
→ grounding validation
→ ADMISSIBLE GroundedGenerationResult
```

Only ADMISSIBLE generations may enter durable generation persistence.

Persistent generation components:

```text
PersistedGroundedGeneration
GroundedGenerationRepository
GroundedGenerationSQLiteStore
SQLiteGroundedGenerationRepository
GroundedGenerationRecordingService
GroundedGenerationHistoryService
```

The durable generation store is downstream evidence, not canonical Knowledge or
History.

## Provider Operational Boundary

Provider usage/cost accounting is immutable and provider-neutral. It has its own
SQLite schema, bounded queries, exact Decimal summaries, readiness validation,
and operational CLI.

This ledger is never a source of investment truth.

## Production Composition

`investment_terminal.server.production:create_app` is the canonical production
factory.

Composition order:

```text
runtime configuration
→ Knowledge repository/query
→ provider generation service
→ usage/cost recorder
→ grounded-generation recorder
→ application services
→ framework-neutral HTTP handler
→ FastAPI adapter
```

FastAPI owns route registration. Production composition passes application
dependencies into the FastAPI factory rather than mutating a returned app.

## Integrated Review Workflow Boundary

The application layer owns the versioned workflow run contract. It records the
canonical stage order, explicit dependencies, stage outcomes, run timestamps,
warnings, failure or skip reasons, and stable artifact identities.

The contract is side-effect free and imports no Review or History internals.
Later composition may invoke public domain services, but orchestration must not
recalculate analysis, collapse immutable archive authority into the SQLite
projection, promote History into Knowledge, or invoke AI implicitly.

The Review domain owns typed evidence assembly across the current portfolio,
canonical current-state market result, external context/sentiment, and market
discovery outputs. Assembly validates identities, time cutoffs, readiness, and
coverage without calculating upstream evidence or generating Review Package
sections. Missing optional inputs remain explicit for the generation stage.

Integrated Review generation reuses the established Review adapters, schema
owner, and atomic exporter. It projects the typed aggregate into the existing
nine-section Review Package, preserves missing evidence and non-authoritative
discovery semantics, and performs no History persistence or comparison.

The History domain owns integrated Review preservation and projection.
`IntegratedReviewHistoryService` first delegates to the existing immutable
archive/manifest service, then synchronizes manifest metadata and imports
details into rebuildable SQLite storage. Archive and projection outcomes stay
separate; projection failure reports the registered snapshot and never removes
or rewrites its canonical archive bytes.

Integrated historical comparison remains read-only and History-owned.
`IntegratedReviewComparisonService` resolves the current imported snapshot,
walks earlier snapshots in reverse canonical order, excludes missing or
non-imported projections, and delegates compatibility and delta calculation to
`HistoricalSnapshotComparisonService`. It distinguishes a true first run from
an unavailable comparison and never invents a zero-change baseline.

The user-facing `investment_terminal.cli.review` composition root executes the
integrated deterministic workflow and writes its versioned run report. It
reuses the live typed market-analysis result, current portfolio snapshot,
integrated Review generator, and History services. Optional context and market
discovery that lack runtime inputs remain explicit gaps. The command has no
Knowledge promotion, AI-provider, broker, or trade-execution dependency.

The command also owns durable failure reporting. It constructs all canonical
stage outcomes, preserves completed artifact identities, marks the first failed
stage and dependent skips, atomically writes the report, and only then exits
non-zero. Projection-after-archive failure is reported without changing the
registered canonical snapshot.

## Runtime Persistence

Dedicated SQLite stores exist for distinct responsibilities, including:

- Knowledge;
- History projection;
- provider usage/cost accounting;
- persisted grounded generations.

Separate databases must not be conflated into a single authority model.

## Runtime Routes

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

Generation-history routes are authenticated and read-only.

## Readiness

Production readiness fails closed when required local prerequisites are absent
or incompatible.

Checks include:

```text
knowledge_database
provider_usage_cost_database
grounded_generation_database
provider_credentials
```

SQLite operational stores are schema-version validated.

## Testing Strategy

Every architectural boundary requires focused unit/integration coverage plus
full regression coverage.

Real network-free E2E tests cover:

- Review Package → History;
- History → Knowledge;
- provider usage/cost persistence;
- Knowledge → grounded generation → durable generation persistence → HTTP
  readback.

## Non-Goals

The current system does not grant autonomous trading authority, broker
execution, causal inference authority, or automatic promotion of AI output into
History/Knowledge.

## Operational Data Baseline

The Phase 7 operational baseline is a read-only application boundary. It opens
configured SQLite inputs in read-only mode, validates known schemas, summarizes
populated ranges and counts, and inspects current portfolio, workflow, and
backup metadata without changing source evidence.

```text
provider configuration names (never secret values)
+ existing operational files and SQLite stores
→ OperationalDataBaselineService
→ versioned deterministic coverage report
```

`CONFIGURED`, `UNCONFIGURED`, `READY`, `ABSENT`, `ERROR`, and `UNMEASURED`
remain distinct. Configured provider capability does not imply populated data;
populated data does not imply freshness, completeness, or approximately
20-year/1000-company coverage. Workflow timing becomes measured only when an
explicit durable workflow report is supplied. The report is operational
evidence, not investment analysis, AI interpretation, or trading authority.

## Yahoo Historical Candle Qualification

Package 2 composes the existing `YahooFinanceClient` behind a narrow
operational service. One explicit instrument, resolution, currency, and
half-open date window produce one immutable qualification result.

```text
explicit bounded request
→ existing YahooFinanceClient
→ identity/window/order validation
→ SUCCESS | EMPTY | FAILED
→ atomic operational report
```

The boundary does not persist candles, retry, schedule, infer analytical
meaning, or qualify other symbols/windows. A `FAILED` report is written before
the CLI exits non-zero. A single `SUCCESS` would establish only that request's
coverage facts, not general reliability, licensing suitability, or long-range
coverage.

Live CLI composition requires an explicit writable yfinance cache directory.
The client configures yfinance to use that caller-owned location instead of an
implicit user-profile cache. Cache ownership is operational state, not market
evidence, and cache contents are never committed or projected into reports.

## Bounded Yahoo Candle Ingestion

After explicit qualification succeeds, one command composes the existing
Yahoo client, historical market service, and candle repository for one symbol
and half-open time window. Runtime owners supply cache, SQLite database, and
atomic report paths. Downloaded, inserted, duplicate, and stored-total counts
remain visible. This boundary does not schedule or authorize bulk ingestion.

The version 2 report obtains earliest/latest stored timestamps with indexed
repository boundary queries. It measures the persisted set without loading its
complete candle history or inferring expected trading sessions.
