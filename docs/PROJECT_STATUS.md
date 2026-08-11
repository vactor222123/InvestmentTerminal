# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 22 — Provider Governance and Usage Controls
implementation complete; final repository verification pending
```

## Completed foundation

### Sprint 12–21

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, provenance/population quality, archive continuity, Knowledge Domain, Evidence-Grounded AI, and the first real OpenAI provider integration are complete.

### Sprint 22 — Provider Governance and Usage Controls

Delivered:

```text
GroundedProviderModelAllowance
GroundedProviderGovernanceAssessment
GroundedProviderGovernancePolicy
mandatory governance enforcement in production composition
explicit live CLI model allowlist
GroundedProviderUsage
provider usage extraction from OpenAI Responses API
provider_usage audit and CLI exposure
GroundedProviderPricingEntry
GroundedProviderPricingPolicy
GroundedProviderCost
deterministic Decimal cost accounting
GroundedProviderCostTraceService
explicit live CLI pricing configuration
GroundedProviderBudgetPolicy
request-side max_output_tokens support
pre-execution output-token budget enforcement
post-execution token budget enforcement
post-execution cost budget enforcement
Sprint 22 control-path E2E
```

## Canonical Live Control Flow

```text
requested provider/model
        ↓
explicit governance allowlist
        ↓
ALLOWED / DENIED
        ↓
pre-execution output-token budget
        ↓
GroundedProviderConfig.max_output_tokens
        ↓
OpenAI Responses API request
        ↓
actual provider usage
        ↓
GroundedProviderUsage
        ↓
explicit pricing policy
        ↓
GroundedProviderCost
        ↓
post-execution token/cost budget validation
        ↓
safe audit trace
        ↓
JSON / human CLI
```

## Governance

Production provider composition is fail-closed.

A provider/model pair must be explicitly present in `GroundedProviderGovernancePolicy` before the production composition path is constructed.

The live CLI has separate concepts:

```text
--model
    requested model

--allow-model
    explicitly allowed model
```

An empty allowlist denies live provider execution.

Governance runs before credential lookup and before provider/network execution.

## Usage Accounting

Provider-neutral usage:

```text
input_tokens
output_tokens
total_tokens
```

OpenAI-specific usage JSON is translated inside the adapter boundary.

`GroundedModelResponse` may carry optional `GroundedProviderUsage`.

`GroundedGenerationTrace` exposes optional `provider_usage`.

Static/reference generation remains backward-compatible and does not require usage.

## Pricing and Cost Accounting

Pricing is explicit configuration, not hardcoded provider knowledge.

A pricing entry contains:

```text
provider_identity
model_identity
currency
input_cost_per_million_tokens
output_cost_per_million_tokens
```

Cost accounting uses deterministic `Decimal` arithmetic.

Unknown provider/model pricing fails closed.

The live CLI accepts explicit pricing inputs and does not contain a default OpenAI price catalog.

## Budget Guardrails

Budget policy supports:

```text
max_output_tokens
max_total_tokens
max_total_cost
currency
```

Pre-execution control:

```text
requested max_output_tokens
→ policy check
→ real OpenAI request max_output_tokens cap
```

Post-execution controls:

```text
actual usage
→ max_output_tokens / max_total_tokens validation

actual estimated cost
→ max_total_cost / currency validation
```

Exact total token usage and exact estimated cost are not misrepresented as pre-flight guarantees because they depend on completed provider usage.

A post-execution budget violation fails closed and no successful report is returned.

## Security and Authority Boundaries

Sprint 22 preserves:

- AI remains downstream of Knowledge;
- raw provider output remains untrusted until parsing and grounding validation;
- provider/model governance cannot be bypassed through a default allowlist;
- API keys remain outside CLI values and audit output;
- Authorization headers, raw HTTP bodies, provider URLs, and raw model text remain excluded from safe traces;
- pricing does not live in the OpenAI adapter;
- budget logic does not live in the Knowledge or grounding domain;
- provider controls do not mutate Knowledge or History;
- no AI persistence schema is introduced;
- no autonomous trading or broker execution is introduced.

## E2E Coverage

Sprint 22 E2E covers:

```text
real Knowledge SQLite
→ governance
→ pre-execution budget
→ provider composition
→ real request max_output_tokens
→ offline-realistic OpenAI response
→ provider usage
→ grounding validation
→ explicit pricing
→ deterministic cost
→ post-execution token validation
→ post-execution cost validation
→ safe report
```

Negative E2E cases verify:

- pre-execution budget denial occurs before query/provider execution;
- observed total-token budget overflow fails closed;
- observed cost overflow fails closed.

No real API key or network access is required for tests.

## Testing Status

Final closure requires:

```text
python -m pytest -q
```

to pass after applying this package.

## Deferred Capabilities

Still deferred:

- retry delay/backoff/jitter;
- `Retry-After` handling;
- provider rate-limit scheduling;
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

Sprint 22 completes fail-closed provider governance plus usage, pricing, and budget controls.

The next milestone should focus on transport resilience and rate-limit behavior or move upward into application/API productization without weakening the existing evidence and governance boundaries.
