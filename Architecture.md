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
