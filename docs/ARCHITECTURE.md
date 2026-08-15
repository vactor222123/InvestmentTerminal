# Investment Terminal — Architecture

## Status

**Document type:** High-level software architecture  
**Document status:** Canonical  
**Updated after:** Sprint 29 — Provider Operational Accounting Hardening  
**Baseline:** `develop @ 1cadd3e`

## 1. Architectural Mission

Investment Terminal is a private, local-first investment intelligence platform
optimized for correctness, determinism, traceability, reproducibility,
explainability, historical integrity, maintainability, and explicit human
decision ownership.

The system is a modular monolith. It preserves verified evidence before
interpretation and keeps AI downstream of traceable Knowledge.

Canonical authority flow:

```text
Current analytical domains
→ Review Package
→ immutable historical archive
→ verified/rebuildable History projection
→ Historical Intelligence / outcome research
→ versioned Knowledge
→ grounded AI context
→ untrusted provider response
→ strict parsing
→ grounding validation
→ application result
→ HTTP/API presentation
→ human decision
```

Parallel operational accounting flow:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
→ bounded operational queries / exact summaries
```

Operational accounting does not become canonical investment evidence.

## 2. Architectural Style

Investment Terminal uses:

- one deployable Python application;
- domain-oriented modules;
- explicit immutable/frozen models where practical;
- application services for orchestration;
- repositories for persistence/query ownership;
- thin CLI and HTTP transport boundaries;
- immutable archive evidence separated from rebuildable projections;
- explicit production composition roots;
- fail-closed governance and runtime controls.

## 3. Domain and Boundary Map

```text
Market / External Data
→ Technical / Fundamental Analysis
→ Ranking / Recommendation
→ Portfolio / Decision
→ Review
→ History
→ Historical Intelligence / Outcome Research
→ Knowledge
→ Grounded AI
→ Application / API
→ Production Server
→ Human Decision
```

Supporting technical boundaries:

```text
Configuration
Persistence
Filesystem
Serialization
Provider transports
Provider operational accounting
CLI
HTTP/FastAPI
Logging
```

## 4. Review Domain

The Review Domain owns the versioned Review Package and assembles already-produced
analytical outputs. It does not own historical persistence, Knowledge derivation,
AI generation, or provider operational accounting.

## 5. History Domain

History preserves completed Review Packages as immutable, verifiable, indexed
historical evidence.

Source-of-truth hierarchy:

```text
Archived JSON = canonical historical evidence
manifest.jsonl = append-only archive index
history.db = rebuildable structured projection
```

Provider usage/cost accounting is explicitly outside this authority.

## 6. Historical Intelligence and Outcome Research

Historical Intelligence operates only on verified historical facts and typed
projections. It must not mutate archive evidence, access live market APIs for
replay, silently recalculate history with current code, or perform fuzzy identity
rewriting.

## 7. Knowledge Domain

Knowledge is a versioned, traceable, rebuildable interpretation layer downstream
of verified historical evidence.

Canonical authority:

```text
History evidence
→ Knowledge record
→ evidence reference
→ grounded AI context
```

Knowledge may be rebuilt. History may not be rewritten.

## 8. Grounded AI Domain

Grounded AI consumes Knowledge through provider-neutral contracts.

Canonical flow:

```text
Knowledge query/context
→ GroundedPromptInput
→ provider-neutral prompt construction
→ provider transport
→ untrusted GroundedModelResponse
→ strict parser
→ grounding validation
→ admissible GroundedGenerationResult
```

Provider output is never canonical evidence merely because a provider returned it.

## 9. Provider Integration and Operational Controls

Established controls include:

- model/provider allowlisting;
- bounded retry execution;
- Retry-After handling;
- deterministic retry-delay policy;
- token usage accounting;
- deterministic pricing/cost accounting;
- output-token limits;
- total-token budgets;
- total-cost budgets;
- explicit provider pricing configuration;
- environment-backed credentials;
- immutable successful usage/cost persistence;
- bounded usage/cost queries;
- exact repository summaries;
- exact SQLite Decimal aggregation.

Canonical production runtime composes provider pricing, budget policies, and
usage/cost recording explicitly.

## 10. Provider Operational Accounting Boundary

Provider operational accounting owns:

- immutable usage/cost ledger records;
- repository query contracts;
- dedicated SQLite storage;
- explicit runtime database path;
- schema versioning/readiness validation;
- bounded recent queries;
- half-open time-window queries;
- exact aggregate summaries;
- operational read-only CLI.

Canonical runtime path:

```text
INVESTMENT_TERMINAL_PROVIDER_USAGE_COST_DATABASE
```

The ledger is operational accounting, not History or Knowledge.

## 11. Application and API Architecture

The application layer exposes provider-neutral orchestration.

```text
GroundedAIApplicationService
→ provider-neutral result/error contracts
→ GroundedAIAPIAdapter
→ GroundedAIHTTPHandler
```

Successful priced usage is recorded downstream of successful application
execution through the operational accounting boundary.

## 12. Production Server Architecture

Canonical production factory:

```text
investment_terminal.server.production:create_app
```

Canonical inbound request flow:

```text
request
→ authentication
→ opaque rate-limit identity derivation
→ rate-limit admission
→ request-size enforcement
→ UTF-8 JSON decoding
→ framework-neutral HTTP handler
→ application/provider execution
→ successful usage/cost recording
→ sanitized response
→ deterministic security headers
```

## 13. Readiness and Runtime Controls

Readiness is network-free and verifies local runtime prerequisites:

```text
knowledge_database
provider_usage_cost_database
provider_credentials
```

Provider usage/cost readiness requires:

```text
configured ledger file
→ valid SQLite
→ schema metadata
→ supported schema version
```

Missing, uninitialized, corrupt, or incompatible ledger storage is `NOT_READY`.

## 14. Runtime Configuration

Production configuration owns:

- Knowledge database path;
- provider usage/cost database path;
- provider model;
- provider allowlist;
- provider timeout/retry limits;
- provider credential environment name;
- provider output/token/cost budgets;
- explicit model pricing and currency;
- inbound server credential environment name;
- maximum request-body size;
- rate-limit capacity/refill rate.

Configuration must fail closed on missing or invalid mandatory controls.

## 15. Persistence and Transaction Ownership

Persistence repositories own SQL/query details.

Important provider-ledger guarantees include:

- immutable request identity;
- exact Decimal text persistence;
- deterministic ordering;
- bounded query ownership;
- exact aggregate summaries;
- schema-version readiness;
- explicit SQLite connection lifecycle.

CLI and HTTP layers must not own SQL.

## 16. CLI Boundary

CLI responsibilities:

```text
parse
→ resolve configuration/paths
→ construct dependencies
→ invoke service/repository boundary
→ format output
→ exit
```

Provider operational CLI is read-only and supports exact request lookup, bounded
recent/time-window queries, and repository-owned summaries.

## 17. Dependency Rules

Allowed direction:

```text
Transport / CLI
→ Application
→ Domain services / repositories
→ Domain models / infrastructure mechanisms
```

Evidence/interpretation direction:

```text
Review
→ History
→ Historical Intelligence / Outcome Research
→ Knowledge
→ Grounded AI
→ Application/API
```

Operational provider accounting remains parallel and downstream of provider
execution; it must not become an upstream source of investment truth.

## 18. Security and Authority Rules

- inbound server credentials are separate from outbound provider credentials;
- secrets must not appear in API responses or rate-limit metadata;
- provider responses remain untrusted until parsing and grounding validation;
- budget/governance controls must be present in canonical production composition;
- unexpected server errors are sanitized;
- request bodies are bounded before decoding;
- supported production rate-limit state is process-local and single-worker;
- provider operational accounting does not gain portfolio mutation authority;
- no autonomous trading or broker execution is introduced.

## 19. Testing Architecture

Critical provider accounting paths include:

```text
runtime environment
→ configured ledger path
→ schema initialization
→ readiness
→ durable record
→ close/reopen
→ bounded queries
→ exact summary
```

Connection lifecycle behavior is covered explicitly because SQLite WAL sidecars
must not remain locked after metadata/readiness operations.

## 20. Intentional Current Limitations

Still intentional:

- rate-limit state is process-local;
- production server supports one worker while that remains true;
- no distributed rate-limit backend;
- no streaming grounded-AI response contract;
- no autonomous portfolio mutation;
- no broker execution;
- no provider-price synchronization service;
- no provider request/response persistence;
- no grounded answer persistence/history.

These are explicit limitations, not hidden claims of support.
