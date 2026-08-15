# Investment Terminal — Architecture Context

## Status

**Document type:** Supporting architecture context  
**Document status:** Synchronized supporting document  
**Primary authority:** `Architecture.md` at repository root  
**Current baseline:** Sprint 31 in progress

This document summarizes the canonical root architecture for readers working
inside `docs/`. If this file and `Architecture.md` ever disagree,
`Architecture.md` is authoritative.

## Authority Flow

```text
Current analytical domains
→ Review Package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ grounded generation
→ grounding validation
→ ADMISSIBLE generated evidence
→ durable grounded-generation persistence
```

Authority does not flow backwards.

- History is canonical historical evidence.
- Knowledge is explicit, versioned, evidence-backed derived knowledge.
- Grounded AI consumes Knowledge.
- Persisted grounded generations are downstream generated evidence only.
- Provider usage/cost accounting is a parallel operational boundary.

No generated AI output becomes History or Knowledge automatically.

## Major Boundaries

```text
Review
→ History
→ Historical Intelligence / Outcome Research
→ Knowledge
→ Grounded AI
→ Application / API
→ Production Server
```

Supporting boundaries include provider transport, provider operational
accounting, configuration, persistence, serialization, CLI, HTTP/FastAPI, and
logging.

## History

Canonical historical source-of-truth hierarchy:

```text
archived Review Package JSON = canonical evidence
manifest.jsonl = append-only navigation/index
history.db = rebuildable structured projection
```

History must not depend on downstream Knowledge, AI, application, API, or server
layers.

## Knowledge

Knowledge owns immutable/versioned records and explicit evidence references.
History-to-Knowledge ingestion is explicit, verified, deterministic, idempotent,
and dry-run capable.

Knowledge is upstream authority for grounded AI and does not depend on AI,
application, API, or server layers.

## Grounded AI

Canonical generation flow:

```text
Knowledge envelopes
→ deterministic selection
→ GroundedPromptInput
→ provider execution
→ strict parsing
→ grounding validation
→ ADMISSIBLE GroundedGenerationResult
```

Only ADMISSIBLE generations may be projected into durable generated evidence.

Persistent generated-evidence components include:

```text
PersistedGroundedGeneration
GroundedGenerationRepository
GroundedGenerationSQLiteStore
SQLiteGroundedGenerationRepository
GroundedGenerationRecordingService
GroundedGenerationHistoryService
```

Persisted generation JSON is deeply immutable in-memory and validated against
the strict JSON value domain before persistence.

## Provider Operational Accounting

Provider usage/cost accounting owns immutable request-level operational records,
bounded queries, exact Decimal summaries, dedicated SQLite storage, schema-aware
readiness, and read-only inspection.

It is never a source of investment truth.

## Production Composition

Canonical production factory:

```text
investment_terminal.server.production:create_app
```

Composition:

```text
runtime configuration
→ persistence repositories
→ provider generation/runtime controls
→ application services
→ framework-neutral HTTP handler
→ FastAPI adapter
```

FastAPI owns route registration. Production composition injects dependencies
into the factory instead of mutating a returned app.

## Runtime Routes

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations?limit=<N>
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

Generation-history routes are authenticated and read-only.

## Readiness

Readiness includes:

```text
knowledge_database
provider_usage_cost_database
grounded_generation_database
provider_credentials
```

Operational SQLite stores are schema-version validated and fail closed when
missing, corrupt, uninitialized, or incompatible.

## Dependency Rules

The enforced authority/dependency direction is:

```text
History
  ✗ Knowledge / AI / Application / API / Server

Knowledge
  ✗ AI / Application / API / Server

AI
  ✓ Knowledge
  ✗ History / Review / Application / API / Server / CLI

Application
  ✓ AI / Knowledge
  ✗ Server / CLI / History internals

API
  ✓ Application
  ✗ Server / CLI / History internals

Server
  ✓ Application / API / AI / Knowledge composition
  ✗ History internals
```

These rules are executable architecture tests.

## Current Limitations

Intentional current limitations include:

- process-local rate-limit state;
- single-worker production server while that remains true;
- no distributed rate-limit backend;
- no deployment container/infrastructure contract yet;
- no authorization model beyond API-key authentication;
- no streaming grounded-AI response contract;
- no automatic promotion of generated evidence into Knowledge or History;
- no autonomous portfolio mutation;
- no broker execution.
