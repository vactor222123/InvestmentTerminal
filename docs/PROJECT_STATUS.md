# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
baseline: 700205d
```

## Current phase

```text
Sprint 23 — Provider Resilience and Rate-Limit Controls
implementation complete
full regression green
ready for closure commit
```

## Completed foundation

### Sprint 12–22

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, provenance/population quality, archive continuity, Knowledge Domain, Evidence-Grounded AI, real OpenAI provider integration, governance, usage, pricing, and budget controls are complete.

### Sprint 23 — Provider Resilience and Rate-Limit Controls

Delivered:

```text
GroundedProviderRetryDelayPolicy
GroundedProviderRetryDelayDecision
GroundedProviderRetryDelayService
GroundedProviderSleeper
TimeGroundedProviderSleeper
explicit retry delay composition
live CLI retry delay configuration
GroundedProviderTransportFailure.retry_after_seconds
Retry-After delta-seconds parsing
Retry-After HTTP-date parsing
GroundedProviderClock
SystemGroundedProviderClock
provider/local delay precedence
applied retry-delay execution metadata
retry-delay audit projection
JSON/human CLI retry-delay visibility
Sprint 23 resilience E2E
```

## Canonical Resilient Live Flow

```text
requested provider/model
        ↓
explicit governance allowlist
        ↓
pre-execution budget guard
        ↓
OpenAI provider request
        ↓
retryable failure?
        ↓ yes
Retry-After metadata
        ↓
deterministic bounded local backoff
        ↓
effective delay = max(local, provider)
        ↓
sleeper
        ↓
bounded retry
        ↓
provider success
        ↓
usage + pricing + post-execution budget validation
        ↓
strict parsing / grounding validation
        ↓
safe operational trace
        ↓
JSON / human CLI
```

## Retry Delay Policy

The local policy is deterministic:

```text
retry 1 = initial_delay
retry 2 = initial_delay × multiplier
retry 3 = initial_delay × multiplier²
...
capped by retry_maximum_delay_seconds
```

The implementation uses `Decimal` for deterministic calculation.

There is no jitter in Sprint 23.

## Retry-After Handling

Supported forms:

```text
Retry-After: <delta-seconds>
Retry-After: <HTTP-date>
```

HTTP-date parsing uses an injectable UTC clock.

Malformed `Retry-After` values are ignored.

Past HTTP-date values become zero delay.

Provider-requested delay is preserved as provider-neutral `retry_after_seconds` metadata.

## Delay Precedence

The effective delay is:

```text
max(local policy delay, provider retry_after_seconds)
```

This guarantees that execution does not retry earlier than either the local backoff policy or the provider-requested delay.

The local maximum caps only local backoff.

It does not truncate a longer provider `Retry-After`.

## Execution Semantics

```text
terminal failure
→ fail immediately
→ no sleep

retryable failure with retries remaining
→ calculate effective delay
→ sleep
→ retry

retryable failure on final attempt
→ fail
→ no extra sleep
```

Retry policy and sleeper must be configured together.

Without retry-delay configuration, the previous zero-delay behavior remains backward-compatible.

## Clock and Sleeper Boundaries

Production:

```text
SystemGroundedProviderClock
TimeGroundedProviderSleeper
```

Tests:

```text
fixed/injected clock
recording/fake sleeper
```

This keeps time-dependent tests deterministic and fast.

## Safe Resilience Audit

Successful provider operational metadata may expose:

```text
attempt_count
retry_count
transport_status_code
transport_outcome
retry_delay_seconds
```

`retry_delay_seconds` is included only when delays were actually applied.

Older exact serialized structures remain unchanged when no delay sequence exists.

Safe audit does not include:

```text
Retry-After header
raw HTTP headers
raw HTTP body
provider failure message
provider URL
Authorization header
API key
raw model text
```

## Live CLI

Retry configuration:

```text
--retry-initial-delay-seconds
--retry-delay-multiplier
--retry-maximum-delay-seconds
```

Human output may show:

```text
Attempts     : 2
Retries      : 1
Retry Delays : 5 s
HTTP Status  : 200
Transport    : SUCCESS
```

JSON output receives the same safe retry-delay metadata through the canonical trace.

## E2E Coverage

Sprint 23 E2E covers:

```text
real Knowledge SQLite
→ rate-limit-like retryable failure
→ provider retry delay
→ local/provider delay precedence
→ deterministic fake sleeper
→ retry
→ successful OpenAI-shaped response
→ grounding validation
→ provider usage
→ safe operational audit
→ human CLI output
```

The E2E explicitly verifies that secrets, raw provider headers, raw rate-limit body text, Authorization data, and `Retry-After` header names do not leak into report or human output.

## Testing Status

Full regression at Sprint 23 closure:

```text
1819 passed, 3 skipped in 8.76s
```

## Security and Authority Boundaries

Sprint 23 preserves:

- AI remains downstream of Knowledge;
- provider retries cannot change evidence authority;
- provider output remains untrusted until strict parsing and grounding validation;
- API keys remain outside audit/CLI output;
- retry metadata is sanitized before reaching audit surfaces;
- provider resilience logic remains outside Knowledge and History;
- no AI persistence schema is introduced;
- no autonomous portfolio mutation is introduced;
- no broker execution is introduced.

## Deferred Capabilities

Still deferred:

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

Sprint 23 completes deterministic provider resilience and server-directed retry timing.

The next milestone should either productize the existing system behind an application/API boundary or add a concurrency-aware provider rate-limit scheduler, without weakening the current evidence, governance, budget, and audit boundaries.
