# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 21 — Provider Integration and Operational AI Controls
implementation complete; final repository verification pending
```

## Completed foundation

### Sprint 12–20

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, provenance/population quality, explicit archive continuity, the deterministic Knowledge Domain foundation, and the provider-neutral Evidence-Grounded AI foundation are complete.

### Sprint 21 — Provider Integration and Operational AI Controls

Delivered:

```text
GroundedProviderConfig
GroundedProviderCredentialSource
StaticGroundedProviderCredentialSource
EnvironmentGroundedProviderCredentialSource
GroundedProviderTransportRequest
GroundedProviderTransportResponse
GroundedProviderTransportFailure
GroundedProviderTransport
StaticGroundedProviderTransport
GroundedProviderExecutionResult
GroundedProviderExecutionService
UrllibGroundedProviderTransport
OpenAIGroundedModelAdapter
OpenAI production composition root
live-ready read-only OpenAI CLI
GroundedProviderOperationalMetadata
provider operational audit trace extension
offline-realistic provider integration E2E
```

## Provider Integration Boundary

The provider stack remains downstream of canonical grounded prompt construction and upstream of strict parsing and grounding validation.

Canonical live flow:

```text
Knowledge / KnowledgeRecordEnvelope
        ↓
deterministic context selection
        ↓
EVIDENCE_GROUNDED_PROMPT@1
        ↓
OpenAIGroundedModelAdapter
        ↓
environment credential source
        ↓
bounded provider execution
        ↓
provider-neutral HTTP transport
        ↓
OpenAI Responses API
        ↓
GroundedModelResponse
        ↓
strict JSON parser
        ↓
EVIDENCE_GROUNDED_ANSWER@1 candidate
        ↓
exact Knowledge grounding validation
        ↓
ADMISSIBLE grounded result
        ↓
safe operational audit trace
```

Raw provider output remains untrusted until parsing and grounding validation succeed.

## Provider Configuration and Credentials

`GroundedProviderConfig` defines:

```text
provider_identity
model_identity
timeout_seconds
max_retries
```

Credentials are resolved through `GroundedProviderCredentialSource`.

The production OpenAI composition uses `EnvironmentGroundedProviderCredentialSource` with an explicitly mapped environment variable:

```text
INVESTMENT_TERMINAL_OPENAI_API_KEY
```

The live CLI accepts an environment-variable name, not an API-key value.

Secrets are not persisted, logged, included in audit traces, or accepted as direct CLI secret arguments.

## Transport and Retry Semantics

`GroundedProviderTransport` is provider-neutral.

The production implementation is:

```text
UrllibGroundedProviderTransport
```

using Python standard-library HTTP transport.

Canonical failure classes:

```text
TIMEOUT
RETRYABLE
TERMINAL
```

Retry semantics are bounded:

```text
maximum attempts = 1 + max_retries
```

Only typed retryable failures are retried. Terminal failures stop immediately.

Current HTTP classification:

```text
408 / 425 / 429 → RETRYABLE
5xx             → RETRYABLE
other 4xx       → TERMINAL
timeout         → TIMEOUT
network URL err → RETRYABLE
```

No sleep/backoff/jitter/rate-limit delay policy is introduced in Sprint 21.

## OpenAI Adapter

`OpenAIGroundedModelAdapter` implements the existing provider-neutral `GroundedModelAdapter` contract.

It uses the OpenAI Responses API through the transport boundary and requests strict structured JSON matching `EVIDENCE_GROUNDED_ANSWER@1`.

The adapter owns provider-specific request/response mapping only.

It does not own:

```text
retry loops
HTTP implementation
environment loading
grounding validation
Knowledge mutation
History mutation
AI persistence
```

## Operational Audit

Successful live provider responses may carry:

```text
attempt_count
retry_count
transport_status_code
transport_outcome
```

`GroundedGenerationTrace` exposes these values as the optional `provider_operation` extension.

Operational audit deliberately excludes:

```text
API keys
Authorization headers
raw HTTP headers
raw HTTP bodies
provider URL
raw model text
```

Static/reference generation remains backward-compatible and does not require operational metadata.

## Live CLI

Sprint 21 adds a separate live-ready read-only CLI.

A real provider/network call requires explicit:

```text
--live
```

The CLI also requires explicit model identity and request/query inputs.

Human output exposes safe operational metadata:

```text
Provider
Model
Attempts
Retries
HTTP Status
Transport
Validation
```

JSON output uses the canonical trace representation.

The Sprint 20 static/reference CLI remains available and does not perform network I/O.

## Stable Guardrails

Sprint 21 preserves these boundaries:

- AI remains downstream of Knowledge;
- provider integration does not mutate Knowledge or History;
- every final claim remains explicitly Knowledge-cited;
- v1 grounding still requires COMPLETE Knowledge provenance;
- raw provider output is never trusted directly;
- strict parsing still precedes grounding validation;
- provider transport and retry policy stay outside domain grounding contracts;
- credentials stay behind an explicit credential-source boundary;
- secrets are excluded from audit/report output;
- live network execution requires explicit CLI opt-in;
- tests do not require a real API key or real network access;
- no embeddings/vector ranking;
- no confidence/truth score;
- no predictive success probability;
- no recommendation-effectiveness semantics;
- no causal inference;
- no autonomous trading or broker execution;
- no AI persistence schema is introduced.

## E2E Coverage

Sprint 21 provider integration E2E covers:

```text
real Knowledge SQLite
→ Knowledge query/envelopes
→ deterministic context selection
→ grounded prompt
→ OpenAI provider composition
→ environment credential lookup
→ bounded retry execution
→ provider transport request
→ offline-realistic Responses API response
→ GroundedModelResponse
→ strict parser
→ exact Knowledge grounding validation
→ ADMISSIBLE generation
→ safe operational trace
```

The E2E uses an injected transport and therefore performs no real network request.

It verifies retry propagation, request correlation, provider/model identity, secret-output isolation, and absence of History/AI persistence.

## Testing Status

Focused Sprint 21 tests are implemented.

Final closure requires:

```text
python -m pytest -q
```

to pass after applying this package.

## Deferred Capabilities

Still deferred:

- streaming provider responses;
- retry delay/backoff/jitter policy;
- `Retry-After` interpretation;
- provider rate-limit scheduling;
- Anthropic/other provider adapters;
- provider/model allowlists;
- token/cost accounting;
- provider request/response persistence;
- semantic entailment verification;
- claim-level contradiction detection;
- relevance ranking or embeddings;
- vector retrieval;
- grounded answer persistence/history;
- human feedback capture;
- prompt-template/version governance beyond current protocol contracts;
- automatic History-to-Knowledge ingestion;
- predictive confidence;
- recommendation effectiveness;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## Next Decision

Sprint 21 makes the Evidence-Grounded AI path live-provider-ready while preserving the Sprint 20 fail-closed grounding boundary.

A future milestone may add provider governance, cost/token observability, additional providers, or controlled streaming, but must not bypass canonical Knowledge provenance, strict parsing, or grounding validation.
