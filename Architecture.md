# Investment Terminal — Software Architecture

## Phase 7 eligibility schema-version-4 boundary

Yahoo symbol-currency qualification is a separate operations boundary after
eligibility-success projection. It verifies the projection checksum, performs
bounded exact-symbol searches, atomically checkpoints private currency evidence,
and exposes only aggregate redacted progress. Typed retry outcomes, a
three-attempt cap, and immediate rate-limit stopping precede any batch request,
candle retrieval, or persistence.

The downstream eligibility-success projection is a separate operations
boundary. It requires the exact source universe and a matching complete
schema-version-4 checkpoint, selects only terminal `SUCCESS` members, and
writes their source/Yahoo identities to a private atomic document. A separate
redacted report exposes only checksums and aggregate counts. The projection
grants no currency, batching, candle-ingestion, ranking, or analysis authority.

`UniverseEligibilityDrainService` is the run-level coordinator over the
unchanged 100-item slice boundary. It owns only bounded repetition, aggregate
progress, and stopping semantics; the slice service retains provider outcome
validation and atomic checkpoint ownership.

The resumable universe eligibility operation owns an explicit schema-version-4
migration. It may reopen only schema-3 terminal `RESPONSE_NUMERIC` evidence for
one fourth production-client attempt. Migration is checkpointed atomically
before provider work; all non-numeric categories retain their three-attempt
boundary. The public report remains aggregate and redacted, and the operation
has no ranking, ingestion, or analysis authority.

**Status:** Canonical architecture  
**Current baseline:** Sprint 30 closure

## Architectural Style

### Phase 7 Critical Product Path

The operational product path is factual data preparation: one private
portfolio input, automatic internet market acquisition, deterministic
persistence and measurements, then an analysis-ready export. Final investment
interpretation belongs to the user or a separate ChatGPT analysis step.

Batch acquisition must isolate failures per instrument. An unresolved ticker,
provider rejection, or incomplete series remains visible without preventing
unrelated instruments from refreshing. Resumability and idempotency are
required before broad-universe execution.

The first bootstrap boundary is sequential and commits per symbol through the
existing candle repository. Its private atomic checkpoint is correlated to a
canonical request checksum. The final report is aggregate and redacted.
`ensure_many` remains fail-fast freshness composition, not a restart boundary.
The implemented `resumable_market_batch` operation owns the restart boundary
and delegates provider access and persistence to existing services.

Automatic broad-US universe acquisition uses official SPY daily fund holdings
under source identity `STATE_STREET_SPY_DAILY_HOLDINGS`. It is not represented
as exact proprietary S&P index membership. Exact raw bytes precede normalized
atomic publication; Yahoo symbols are a separate deterministic projection.

The SPY direction is superseded before implementation. Broad automatic
acquisition instead uses the official Nasdaq Trader `nasdaqlisted.txt` and
`otherlisted.txt` directories under `BROAD_US_LISTED_SECURITIES`. Both exact
files are archived before a typed normalized universe is atomically published.
`nasdaq_universe_qualification` implements this boundary without composing
downstream candle requests.

`universe_eligibility_scan` is the next separate operations boundary. It binds
the canonical private universe checksum to one explicit 90-day Yahoo OHLCV
window, atomically checkpoints at most 100 deterministic pending outcomes per
invocation, and publishes redacted aggregate progress. Terminal failures are
isolated and exact resume performs no provider work for completed outcomes.
The boundary does not rank members, generate ingestion requests, or persist
candles.

Eligibility checkpoint/report schema version 2 adds a typed retry boundary.
The Yahoo adapter classifies only in-memory exception types; operations persist
stable privacy-safe categories. Schema-1 migration is atomically published
before provider work, retry-pending members precede new members, each provider
identity has a three-attempt cap, and the first rate-limit category halts the
invocation. Completed evidence remains terminal and no automatic scheduling or
sleep occurs.

Schema version 3 adds typed local invalid-response diagnostics. It atomically
migrates eligible schema-2 terminal `INVALID_RESPONSE` evidence to one final
retry while preserving all other evidence and the existing attempt cap.

`single_series_candle_diagnostic` is a separate read-only operations boundary.
It deterministically selects one terminal `RESPONSE_NUMERIC` outcome from a
validated schema-3 checkpoint, repeats only that raw 90-day Yahoo request, and
publishes timestamps plus stable defect types without identities or values. It
does not mutate the checkpoint, weaken production candle validation, continue
the universe scan, or persist candles.

The first controlled diagnostic returned 48 valid rows and no reproducible
defect. Because schema 3 treats `RESPONSE_NUMERIC` as terminal, its checkpoint
can retain a stale ineligibility outcome after the provider response recovers.
The selected next boundary is an atomic schema-4 migration with one additional
production-client revalidation allowance for numeric failures only. OHLC,
no-price, and all unrelated terminal evidence remain unchanged.

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
populated ranges and counts, and inspects current portfolio, workflow, backup,
and optional single-instrument refresh metadata without changing source evidence.

```text
provider configuration names (never secret values)
+ existing operational files and SQLite stores
→ OperationalDataBaselineService
→ versioned deterministic coverage report
```

`CONFIGURED`, `UNCONFIGURED`, `READY`, `ABSENT`, `ERROR`, and `UNMEASURED`
remain distinct. Configured provider capability does not imply populated data;
populated data does not imply freshness, completeness, or approximately
20-year/1000-company coverage. Refresh observability and performance become
measured only when an explicit valid durable workflow or refresh report is
supplied. Omitting the refresh input preserves the schema-version-1 eight-store
shape; an explicit refresh input conditionally adds `REFRESH_REPORT`. Invalid
evidence remains visible as `ERROR` and cannot produce `READY`. These reports
are operational evidence, not investment analysis, AI interpretation, or
trading authority.

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

## Bounded Market-Data Refresh Observability

The single-instrument refresh command composes the existing Yahoo client,
repository, freshness service, and refresh service for one explicit identity
and checked-at time. Its versioned atomic report preserves freshness before and
after, whether refresh was attempted, the exact import result, duration, and a
visible failure.

`SUCCESS`, `NOT_READY`, and `FAILED` remain distinct. A refresh that completes
without making the series fresh exits non-zero as `NOT_READY`; provider and
persistence exceptions are reported before a non-zero exit. The boundary does
not schedule, retry, refresh multiple instruments, analyze prices, or authorize
trading.

## Explicit-Session Candle Coverage Quality

History owns deterministic comparison of daily candle dates with an explicitly
supplied, versioned local session calendar. The evaluator reports expected,
observed, missing, and unexpected evidence. It never infers sessions from
weekdays, exchange names, or candle presence.

Bounded XNAS evidence has separate immutable calendar identities: `XNAS@1` for
the audited one-year window and `XNAS@2` for the audited five-year MSFT window.
Version 2 retains all official annual calendar source URIs plus the official
exceptional-close alert. Neither version authorizes dates outside its bounds.

XNYS evidence is separately owned and versioned. `XNYS@1` covers only the
audited 2021-08-19 through 2026-08-18 window, cites official ICE/NYSE calendar
announcements and the exceptional-close memorandum, and never reuses XNAS
identity or provenance even where observed session dates coincide.

## Transaction CSV Qualification

The bounded transaction qualification command composes the canonical CSV
parser into a parse-only operational boundary. It atomically exports a redacted
schema-version-1 `SUCCESS`, `EMPTY`, or `FAILED` report before any non-zero
failure exit. Aggregate type/count/time coverage is visible; source paths,
identities, instruments, monetary values, references, and raw rows are excluded.
The boundary has no SQLite, valuation, workflow, AI, or trading dependency.

## Atomic Portfolio Transaction Import

The Portfolio repository contract owns row-aligned atomic batch append. The
in-memory adapter stages the complete candidate state before publishing it; the
SQLite adapter uses one store transaction for the complete batch. Existing and
repeated identities are deterministic duplicates, while any unexpected durable
failure rolls back every new row from that batch. `TransactionImportService`
maps these outcomes into the existing import-result JSON without changing its
schema. No CLI, runtime database mutation, valuation, workflow, or trading
authority is implied by this persistence boundary.

The bounded `transaction_csv_import` composition root parses before database
initialization, binds explicit immutable ledger metadata, delegates the complete
batch to that atomic boundary, and atomically writes a schema-version-1 redacted
operational report. Reports contain aggregate counts and stored time coverage
only. Source/database paths and transaction, ledger, portfolio, instrument, and
monetary identities remain private. SQLite commit and report replacement are
separate side effects: a post-commit report failure is raised distinctly and is
reconciled by rerunning the same immutable identities after repairing output.
Bounded transaction-derived valuation composes Portfolio-owned ledger,
reconstruction, realised/unrealised, quote, snapshot, and SQLite boundaries.
The CLI owns explicit runtime paths and atomic redacted reporting; private
valuation evidence remains in the valuation database.
Offline quote qualification is a read-only Portfolio boundary that produces
redacted aggregate evidence and never valuation persistence.
Optional schema-version-1 instrument metadata is a separate private evidence
input with explicit source provenance and caller-owned maximum age. Enrichment
creates a detached open-position projection, requires exact `READY` coverage,
and never rewrites immutable transaction payloads.
The bounded OpenFIGI bootstrap independently confirms ISIN-to-ticker candidates,
preserves exact provider response bytes privately, and publishes the existing
metadata document plus a redacted aggregate report. Provider exchange codes are
not treated as MICs, and candidate ticker absence fails closed.
Its versioned report exposes only a stable privacy-safe failure category;
provider text, exception messages, identities, paths, and credentials remain
private.
When the confirmed candidate ticker is present among multiple listings,
metadata construction filters to all candidate-ticker FIGIs deterministically;
candidate absence and missing candidate FIGIs remain fail-closed.
Candidate absence optionally carries a typed private diagnostic to the CLI.
The CLI writes that schema-version-1 document atomically to an explicit local
path before the unchanged schema-version-3 redacted report. Diagnostic-write
failure remains non-zero and cannot mutate metadata or expose private values.
Bounded Yahoo ISIN-search qualification is a separate discovery boundary. It
reads the private ISIN diagnostic, queries Yahoo with unrelated content
disabled, writes normalized candidates privately, and exposes only aggregate
redacted coverage. Yahoo discovery never selects or mutates metadata by itself.
Exact Yahoo ticker-match qualification joins one private diagnostic, its Yahoo
candidate document, and one existing private quote. Only a unique exact ticker
match produces private evidence; the shareable report remains aggregate.
