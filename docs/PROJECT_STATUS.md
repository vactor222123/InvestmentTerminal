# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 20 — Evidence-Grounded AI Experience Foundation
implementation complete; final repository verification pending
```

## Completed foundation

### Sprint 12–19

Historical Intelligence, comparison/replay, outcome observations, methodology hardening, descriptive research, provenance/population quality, explicit archive continuity, and the deterministic Knowledge Domain foundation are complete.

### Sprint 20 — Evidence-Grounded AI Experience Foundation

Delivered:

```text
GroundedKnowledgeCitation
GroundedAIClaim
GroundedAIAnswer
GroundingValidationAssessment
GroundingValidationService
GroundedContextSelectionPolicy
GroundedContextSelection
GroundedContextSelectionService
GroundedPromptContextItem
GroundedPromptInput
GroundedPromptInputService
GroundedModelAdapter
GroundedModelResponse
StaticGroundedModelAdapter
GroundedModelParseResult
GroundedModelResponseParser
GroundedGenerationResult
GroundedGenerationService
GroundedGenerationTrace
GroundedGenerationTraceService
read-only Grounded AI reference CLI
real Knowledge SQLite → grounded reference workflow E2E
```

## AI Domain Boundary

The AI layer is downstream of Knowledge and consumes immutable `KnowledgeRecordEnvelope` values.

Canonical dependency direction:

```text
History / verified evidence
        ↓
Knowledge
        ↓
KnowledgeRecordEnvelope
        ↓
AI context selection
        ↓
grounded prompt input
        ↓
model adapter boundary
        ↓
raw model response
        ↓
strict response parser
        ↓
candidate GroundedAIAnswer
        ↓
grounding validation
        ↓
ADMISSIBLE grounded result
```

AI must not mutate History or Knowledge.

## Canonical Protocols

Sprint 20 introduces two explicit versioned contracts:

```text
EVIDENCE_GROUNDED_PROMPT@1
EVIDENCE_GROUNDED_ANSWER@1
```

`GroundedPromptInput` is provider-neutral and contains:

```text
request_id
protocol_identity
user_query
context
```

Each context item preserves:

```text
knowledge_identity
subject_key
statement
provenance_status
valid_from
valid_to
```

## Grounded Answer Contract

Every `GroundedAIClaim` must have at least one explicit `GroundedKnowledgeCitation`.

Citation fields:

```text
knowledge_identity
statement
provenance_status
```

A citation is not trusted merely because it is present. `GroundingValidationService` must resolve it against supplied `KnowledgeRecordEnvelope` values.

## Grounding Admissibility

`EVIDENCE_GROUNDED_ANSWER@1` v1 requires:

```text
exact Knowledge identity resolution
exact statement match
exact provenance status match
Knowledge provenance = COMPLETE
```

`PARTIAL` Knowledge provenance remains traceable but is not admissible grounding for v1.

This rule is a lineage/admissibility rule. It is not a truth score, confidence score, semantic entailment proof, causal proof, or effectiveness assessment.

## Context Selection

AI context selection is deterministic and explicit.

Supported policy:

```text
subject_keys
max_items
required provenance = COMPLETE
```

Canonical presentation order:

```text
subject_key
→ valid_from
→ generated_at
→ knowledge_id
→ version
```

No embedding, semantic similarity, relevance score, or model-based ranking exists in Sprint 20.

## Model Adapter Boundary

`GroundedModelAdapter` is provider-independent.

The canonical raw response contract is:

```text
request_id
provider_identity
model_identity
raw_text
```

Sprint 20 includes only `StaticGroundedModelAdapter` as a deterministic reference/test adapter.

No real provider SDK, API key handling, HTTP client, endpoint configuration, retry policy, rate-limit handling, or network I/O is implemented.

## Response Parsing

`GroundedModelResponseParser` is JSON-only and fail-closed.

The exact response shape is:

```text
answer_id
protocol_identity
claims[]
  text
  citations[]
    knowledge_identity
    statement
    provenance_status
```

Missing or unsupported fields fail explicitly.

Parsing only establishes structural validity. Grounding admissibility is checked separately.

## Orchestration

`GroundedGenerationService` composes:

```text
selection
→ prompt
→ adapter
→ response
→ parser
→ grounding validation
```

The workflow is fail-closed.

Malformed JSON, request-correlation mismatch, unresolved citation, forged statement, forged provenance status, or excluded context cannot become a final grounded answer.

A successful `GroundedGenerationResult` requires:

```text
validation.status = ADMISSIBLE
```

## Audit Trace

`GroundedGenerationTrace` provides a compact deterministic lifecycle representation:

```text
request_id
prompt_protocol_identity
answer_protocol_identity
provider_identity
model_identity
selected_knowledge_identities
cited_knowledge_identities
claim_count
citation_count
validation_status
```

Cited Knowledge identities must be a subset of selected context.

The trace deliberately excludes raw model text, full statements, user query text, API credentials, and provider payloads.

## Read-only Reference CLI

Sprint 20 provides a reference CLI using the static adapter only.

Inputs include:

```text
--database
--request-id
--query
--response-json
--subject
--max-items
--json
```

The CLI reads Knowledge SQLite, runs the grounded workflow, builds an audit trace, and renders human/JSON output.

It does not call a real model or perform network I/O.

## Stable Guardrails

Sprint 20 preserves these boundaries:

- AI remains downstream of Knowledge;
- AI does not mutate Knowledge or History;
- every final claim is explicitly Knowledge-cited;
- v1 grounding requires COMPLETE Knowledge provenance;
- raw model output is never trusted directly;
- strict parsing happens before grounding validation;
- grounding validation is separate from semantic entailment;
- context selection is deterministic and non-semantic;
- no embeddings/vector ranking;
- no confidence/truth score;
- no predictive success probability;
- no recommendation-effectiveness semantics;
- no causal inference;
- no autonomous trading or broker execution;
- no real provider SDK or network integration;
- no AI persistence schema is introduced;
- CLI remains read-only composition/rendering.

## E2E Coverage

Sprint 20 covers:

```text
real Knowledge SQLite
→ Knowledge query/envelopes
→ deterministic context selection
→ grounded prompt
→ static reference model response
→ strict parser
→ grounding validation
→ ADMISSIBLE generation result
→ audit trace
→ JSON/human CLI
```

The E2E also verifies that the reference AI workflow creates neither History persistence nor AI persistence and exposes no network/provider configuration.

## Testing Status

Focused Sprint 20 tests are implemented.

Final closure requires:

```text
python -m pytest -q
```

to pass after applying this package.

## Deferred Capabilities

Still deferred:

- real OpenAI/Anthropic/other provider adapters;
- API key/secret management;
- HTTP/network transport;
- retries, rate limits, timeout policy, streaming;
- structured-output provider configuration;
- semantic entailment verification;
- claim-level contradiction detection;
- relevance ranking or embeddings;
- vector retrieval;
- grounded answer persistence/history;
- human feedback capture;
- prompt-template/version governance beyond the current protocol contracts;
- model/provider allowlists;
- cost/token accounting;
- automatic History-to-Knowledge ingestion;
- predictive confidence;
- recommendation effectiveness;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## Next Decision

Sprint 20 establishes a deterministic, provider-neutral, fail-closed Evidence-Grounded AI foundation.

A future provider-integration milestone may attach a real model only through `GroundedModelAdapter` and must preserve the existing prompt, parser, grounding-validation, audit, and domain-boundary contracts.
