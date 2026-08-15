# Investment Terminal — Architecture

## Status

**Document type:** High-level software architecture  
**Document status:** Canonical  
**Updated after:** Post-Sprint-26 Audit Fix 1  
**Baseline:** `develop @ ad9dd1f`

## 1. Architectural Mission

Investment Terminal is a private, local-first investment intelligence platform optimized for correctness, determinism, traceability, reproducibility, explainability, historical integrity, maintainability, and explicit human decision ownership.

The system is a modular monolith. It preserves verified evidence before interpretation and keeps AI downstream of traceable Knowledge.

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

No AI or API boundary may rewrite canonical historical evidence or autonomously mutate portfolio state.

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
CLI
HTTP/FastAPI
Logging
```

## 4. Review Domain

The Review Domain owns the versioned Review Package and assembles already-produced analytical outputs.

It does not own:

- market-data acquisition;
- indicator calculations;
- portfolio valuation rules;
- recommendation rules;
- historical persistence;
- Knowledge derivation;
- AI generation.

## 5. History Domain

History preserves completed Review Packages as immutable, verifiable, indexed historical evidence.

It owns:

- snapshot identity;
- exact-byte immutable archive;
- archive path confinement;
- SHA-256 verification;
- append-only manifest;
- SQLite schema and migrations;
- explicit import state;
- structured historical import;
- timeline persistence;
- History repositories;
- verified archived package loading.

Source-of-truth hierarchy:

```text
Archived JSON = canonical historical evidence
manifest.jsonl = append-only archive index
history.db = rebuildable structured projection
```

A failed detail import must not leave a misleading partial projection.

## 6. Historical Intelligence and Outcome Research

Historical Intelligence operates only on verified historical facts and typed projections.

It owns:

- snapshot compatibility;
- portfolio-summary comparison;
- holdings comparison;
- recommendation comparison;
- deployment comparison;
- aggregate snapshot comparison;
- exact and normalized replay semantics;
- outcome observations;
- descriptive outcome research;
- methodology identity;
- provenance/population-quality assessment.

It must not:

- mutate archive evidence;
- access live market APIs for replay;
- silently recalculate history with current code;
- perform fuzzy identity rewriting.

## 7. Knowledge Domain

**Status: Implemented.**

Knowledge is a versioned, traceable, rebuildable interpretation layer downstream of verified historical evidence.

It owns:

- immutable/versioned Knowledge records;
- evidence references;
- provenance assessment;
- deterministic projection/query/comparison;
- read-only Knowledge access boundaries.

Knowledge may be rebuilt. History may not be rewritten.

Canonical authority:

```text
History evidence
→ Knowledge record
→ evidence reference
→ grounded AI context
```

Knowledge is not allowed to mutate History.

## 8. Grounded AI Domain

**Status: Implemented.**

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

Grounding validation is a mandatory trust boundary.

## 9. Provider Integration and Operational Controls

The OpenAI provider is composed behind provider-neutral interfaces.

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
- environment-backed credentials.

Canonical production runtime now composes provider pricing and budget policies explicitly.

Economic controls are fail-closed in production configuration: canonical production startup requires explicit budget and pricing settings.

## 10. Application and API Architecture

The application layer exposes provider-neutral orchestration.

```text
GroundedAIApplicationService
→ provider-neutral result/error contracts
→ GroundedAIAPIAdapter
→ GroundedAIHTTPHandler
```

The framework-neutral HTTP handler owns deterministic application-to-HTTP mapping.

FastAPI is a transport adapter, not the owner of application/domain rules.

## 11. Production Server Architecture

Canonical production factory:

```text
investment_terminal.server.production:create_app
```

Canonical CLI:

```text
python -m investment_terminal.cli.server
```

Runtime routes:

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /openapi.json
```

Swagger `/docs` and ReDoc `/redoc` are disabled.

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
→ sanitized response
→ deterministic security headers
```

Authentication occurs before rate-limit admission.

## 12. Authentication and Request Controls

`POST /v1/grounded-ai` requires inbound `X-API-Key` authentication.

Established server controls:

- inbound API-key authentication;
- bounded request bodies before JSON decoding;
- sanitized unexpected-error handling;
- deterministic security headers;
- process-local token-bucket rate limiting;
- safe `RateLimit-*` client metadata;
- `429` plus `Retry-After`;
- fail-closed single-worker production runtime while limiter state is process-local.

Unauthenticated requests:

```text
→ 401
→ no authenticated rate-limit token consumed
→ no RateLimit-* state exposed
```

## 13. Runtime Configuration

Production configuration owns:

- Knowledge database path;
- provider model;
- provider allowlist;
- provider timeout/retry limits;
- provider credential environment name;
- provider output/token/cost budgets;
- explicit model pricing and currency;
- inbound server credential environment name;
- maximum request-body size;
- rate-limit capacity/refill rate.

Configuration must fail closed on missing or invalid mandatory economic controls.

## 14. Persistence and Transaction Ownership

Persistence repositories own SQL/query details.

Important integrity guarantees include:

- immutable archive creation;
- exact-byte checksum verification;
- path confinement;
- append-only manifest behavior;
- controlled schema migration;
- explicit import state;
- atomic historical detail import;
- deterministic ordering;
- rebuildable SQLite projections.

CLI and HTTP layers must not own SQL.

## 15. CLI Boundary

CLI responsibilities:

```text
parse
→ resolve configuration/paths
→ construct dependencies
→ invoke service/repository boundary
→ format output
→ exit
```

Forbidden:

- business rules in CLI;
- direct SQL where repository boundaries exist;
- hidden historical recalculation;
- archive mutation from read-only commands.

## 16. Dependency Rules

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

Forbidden examples:

```text
History → live market API
History → current analysis recalculation
Historical Intelligence → archive mutation
Knowledge → History mutation
AI → canonical historical rewrite
FastAPI → domain-rule ownership
CLI → domain-rule ownership
```

## 17. Security and Authority Rules

- inbound server credentials are separate from outbound provider credentials;
- secrets must not appear in API responses or rate-limit metadata;
- provider responses remain untrusted until parsing and grounding validation;
- budget/governance controls must be present in canonical production composition;
- unexpected server errors are sanitized;
- request bodies are bounded before decoding;
- supported production rate-limit state is process-local and single-worker;
- no autonomous trading or broker execution is introduced.

## 18. Testing Architecture

Important behaviors require focused tests plus full regression.

Critical end-to-end paths include:

```text
Review Package
→ Archive
→ Verification
→ History import
→ Timeline
→ Comparison / Replay
```

```text
History
→ Knowledge
→ Grounded prompt
→ Provider
→ Parsing
→ Grounding validation
```

```text
Runtime environment
→ production.create_app()
→ authentication
→ rate limiting
→ HTTP handler
→ application/provider controls
→ response
```

Passing unit tests do not replace production composition tests.

## 19. Intentional Current Limitations

Still intentional:

- rate-limit state is process-local;
- production server supports one worker while that remains true;
- no distributed rate-limit backend;
- no streaming grounded-AI response contract;
- no autonomous portfolio mutation;
- no broker execution;
- no provider-price synchronization service;
- no persistent usage/cost ledger unless introduced by a future milestone.

These are explicit limitations, not hidden claims of support.
