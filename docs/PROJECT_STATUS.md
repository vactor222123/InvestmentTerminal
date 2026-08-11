# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: 85eb416
```

## Current phase

```text
Sprint 24 — Application/API Productization Foundation
implementation complete
full regression green
ready for closure commit
```

## Completed foundation

### Sprint 12–23

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, provenance/population quality, archive continuity, Knowledge Domain, Evidence-Grounded AI, real OpenAI provider integration, governance, usage, pricing, budget controls, and provider resilience are complete.

### Sprint 24 — Application/API Productization Foundation

Delivered:

```text
GroundedAIApplicationRequest
GroundedAIApplicationResult
GroundedAIApplicationService
LiveGroundedAIApplicationService
build_live_grounded_ai_application()
GroundedAIApplicationFailureDetails
GroundedAIApplicationError
GroundedAIAPIRequest
GroundedAIAPIResponse
GroundedAIAPIAdapter
GroundedAIHTTPResponse
GroundedAIHTTPStatusMapper
GroundedAIHTTPHandler
build_live_grounded_ai_http_handler()
```

## Canonical Productization Flow

```text
future server/runtime adapter
        ↓
API composition
        ↓
GroundedAIHTTPHandler
        ↓
GroundedAIAPIRequest
        ↓
GroundedAIAPIAdapter
        ↓
GroundedAIApplicationService
        ↓
Knowledge / GroundedGeneration / provider stack
        ↓
GroundedAIApplicationResult
        ↓
GroundedAIAPIResponse
        ↓
HTTP status mapping
        ↓
GroundedAIHTTPResponse
```

## Application Contract

Request:

```text
request_id
user_query
subject_keys
max_items
```

Result:

```text
generation
trace
```

The application boundary owns use-case orchestration, not CLI parsing, HTTP framework integration, database construction, provider composition, credential lookup, or persistence.

## Application Error Contract

Stable categories:

```text
POLICY_DENIED
INVALID_REQUEST
EXECUTION_FAILED
INTERNAL_ERROR
```

Stable codes:

```text
APPLICATION_POLICY_DENIED
APPLICATION_INVALID_REQUEST
APPLICATION_EXECUTION_FAILED
APPLICATION_INTERNAL_ERROR
```

Known lower-level exceptions are mapped to stable application errors.

The original exception remains available internally as `__cause__`.

Unknown internal failures return a sanitized application error message.

## Application Composition

`build_live_grounded_ai_application()` owns:

```text
Knowledge SQLite store
→ Knowledge repository
→ Knowledge query service

provider composition
→ Grounded generation service

both
→ LiveGroundedAIApplicationService
```

This removes Knowledge/provider construction from external adapters.

## CLI Status

The CLI now:

```text
parses input
→ builds governance/pricing/budget policy values
→ calls application composition
→ creates GroundedAIApplicationRequest
→ renders GroundedAIApplicationResult
```

It no longer directly constructs the Knowledge SQLite stack or primary provider/application orchestration path.

Legacy `_run_live()` is retained for backward-compatible programmatic tests/callers.

## API Contract

Request:

```text
request_id
query
subjects
max_items
```

Unknown fields are rejected.

Success:

```text
status = SUCCESS
request_id
data = {
  generation,
  trace
}
```

Error:

```text
status = ERROR
request_id
error = {
  category,
  code,
  message
}
```

## HTTP Mapping

```text
SUCCESS          → 200
INVALID_REQUEST  → 400
POLICY_DENIED    → 403
EXECUTION_FAILED → 503
INTERNAL_ERROR   → 500
unknown category → 500
```

Unknown failure categories fail closed to HTTP 500.

## Framework-Neutral HTTP Handler

The handler accepts an already-decoded payload and owns:

```text
payload validation
→ API request mapping
→ application execution
→ API response mapping
→ HTTP status mapping
```

Malformed payloads become stable HTTP 400 responses.

If no valid client request id exists, the error response uses `UNKNOWN` rather than inventing a new identity.

## API Composition

`build_live_grounded_ai_http_handler()` owns:

```text
build_live_grounded_ai_application()
→ GroundedAIHTTPHandler
```

A future FastAPI/Flask/other server adapter can depend on this one composition boundary.

## Current Non-Goals

Sprint 24 intentionally does not provide:

```text
running HTTP server
route registration
FastAPI/Flask dependency
authentication middleware
authorization middleware
OpenAPI schema publication
health/readiness route
deployment container/runtime
```

Those belong to the next productization stage.

## Testing Status

Full regression at Sprint 24 closure:

```text
1865 passed, 3 skipped in 9.04s
```

Focused Sprint 24 tests cover:

```text
application boundary
application orchestration
fail-fast budget ordering
CLI migration
application composition
CLI composition migration
application error contract
API contract
HTTP status mapping
HTTP handler
API composition
```

## Security and Authority Boundaries

Sprint 24 preserves:

- AI remains downstream of Knowledge;
- no API adapter can bypass grounding validation;
- provider/model governance remains fail-closed;
- provider credentials remain outside API/application contracts;
- raw transport data remains outside API responses;
- policy denials are explicit and stable;
- unknown internal failures are sanitized;
- no API/HTTP path mutates Knowledge or History;
- no AI persistence schema is introduced;
- no autonomous portfolio mutation is introduced;
- no broker execution is introduced.

## Deferred Capabilities

Still deferred:

- concrete web-framework runtime;
- server routes/startup;
- authentication and authorization;
- API schema publication/OpenAPI;
- health/readiness endpoints;
- deployment/runtime packaging;
- inbound API rate limiting;
- retry jitter;
- proactive provider rate-limit scheduling;
- concurrency-aware throttling;
- streaming responses;
- additional provider adapters;
- provider pricing catalog synchronization;
- cached-token/reasoning-token pricing differentiation;
- persistent usage/cost ledger;
- provider request/response persistence;
- semantic entailment validation;
- contradiction detection;
- vector retrieval/embeddings;
- grounded answer persistence/history;
- automatic History-to-Knowledge ingestion;
- predictive confidence/effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## Next Decision

Sprint 24 completes the framework-neutral application/API productization foundation.

The next milestone should add a real server/runtime adapter over the existing API composition boundary, with authentication and deployment concerns introduced incrementally rather than embedded into the application layer.
