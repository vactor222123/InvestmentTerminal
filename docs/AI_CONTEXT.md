# InvestmentTerminal AI Context

## Mission

InvestmentTerminal is a private, local-first investment intelligence platform for deterministic analysis, transparent decisions, preserved historical evidence, traceable Knowledge, and evidence-grounded AI assistance.

The system should explain:

- what it currently concludes;
- which evidence produced that conclusion;
- what it concluded previously;
- why historical conclusions changed;
- what Knowledge was supplied to AI;
- why a grounded AI result was admissible or rejected.

## Current Architecture

```text
market / external data
→ technical and fundamental analysis
→ ranking / recommendation
→ portfolio / decision
→ review package
→ immutable archive + append-only manifest
→ verified SQLite History projection
→ historical intelligence / outcome research
→ versioned Knowledge
→ grounded prompt/context
→ provider execution
→ strict parsing + grounding validation
→ application/API
→ production HTTP server
→ human decision
```

## Primary Domains and Boundaries

- portfolio;
- market and external data;
- technical/fundamental analysis;
- ranking/recommendation;
- decision;
- review;
- history;
- historical intelligence;
- outcome research;
- knowledge;
- grounded AI;
- provider integration/governance;
- application/API;
- production server.

## Authority Hierarchy

```text
immutable archived Review Package
→ verified History
→ versioned Knowledge + evidence references
→ GroundedPromptInput
→ untrusted provider response
→ strict parser
→ grounding validation
→ admissible grounded generation
```

AI output does not become canonical historical evidence automatically.

## Composition Boundaries

### CLI

CLI modules:

- resolve arguments and paths;
- construct services;
- orchestrate workflows;
- format output/errors.

CLI must not own business rules or SQL that belongs behind repository/service boundaries.

### History

History preserves immutable evidence and builds rebuildable query projections.

```text
archive
→ manifest
→ verified load
→ SQLite projection
→ timeline
```

History must not access live market APIs or recalculate historical facts with current analysis code.

### Knowledge

Knowledge derives versioned, traceable records from verified evidence.

Knowledge may be rebuilt. History may not be rewritten.

### Grounded AI

Grounded AI consumes Knowledge, not raw authority-free provider text.

Provider output remains untrusted until strict parsing and grounding validation succeed.

### Application/API

Application orchestration is provider-neutral.

HTTP mapping remains framework-neutral before FastAPI transport composition.

### Production Server

Canonical production runtime:

```text
investment_terminal.server.production:create_app
```

Canonical server CLI:

```text
python -m investment_terminal.cli.server
```

Inbound grounded-AI flow:

```text
authentication
→ rate-limit identity
→ rate-limit admission
→ request-size enforcement
→ JSON decoding
→ HTTP handler
→ application/provider execution
→ sanitized response
```

## Provider and Economic Controls

Canonical production composition includes:

- provider/model allowlisting;
- bounded retry/resilience;
- output-token limit;
- total-token budget;
- total-cost budget;
- explicit pricing policy;
- usage/cost accounting;
- environment-backed provider credentials.

Provider pricing is explicit configuration and must not be treated as hardcoded permanent truth.

## Server Security Controls

Established controls include:

- separate inbound server and outbound provider credentials;
- inbound API-key authentication;
- bounded request bodies;
- sanitized unexpected errors;
- deterministic security headers;
- process-local token-bucket rate limiting;
- safe `RateLimit-*` metadata;
- `429` + `Retry-After`;
- single-worker production enforcement while rate-limit state is process-local.

Unauthenticated requests do not consume authenticated rate-limit capacity and do not expose limiter state.

## Engineering Principles

1. Reliability over cleverness.
2. Correctness before convenience.
3. Deterministic behavior and stable ordering.
4. Explicit contracts over implicit conventions.
5. Preserve evidence before interpretation.
6. Keep public contracts stable.
7. Prefer focused changes over broad rewrites.
8. Reuse proven infrastructure.
9. Refactor only when it reduces demonstrated complexity or risk.
10. Tests and documentation are part of implementation.
11. Production composition must prove that established controls are actually wired.
12. Fail closed when a required governance, integrity, security, or economic control is missing.

## Established Technical Rules

- Persisted/exported timestamps are timezone-aware.
- UTC is the canonical storage timezone.
- Historical archive bytes are immutable.
- Historical archive creation is exclusive.
- Manifest storage is append-only JSON Lines.
- Checksums verify archived evidence.
- SQLite History is not the source of truth.
- External provider payloads are normalized before core use.
- Missing data remains distinguishable from weak data.
- Shared primitive validation belongs in `investment_terminal.utils.validation`.
- Domain-specific validation remains in the owning domain.
- Provider responses are untrusted before grounding validation.
- Provider pricing is explicit configuration.
- Production rate-limit state is process-local under the supported single-worker runtime.

## Required Reading Before Major Changes

Read current canonical documents first:

- `docs/AI_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MAP.md`
- `docs/PROJECT_STATUS.md`
- `Roadmap.md`
- relevant domain documentation;
- relevant implementation and tests.

Historical sprint plans/reviews are supporting history, not current architecture authority.

## Decision Policy

Before introducing a new abstraction, confirm that it:

- solves an observed problem;
- reduces duplication or risk;
- respects domain ownership;
- has focused tests;
- is expected to be reused or materially improves a critical boundary.

Before changing an established contract, document:

- why the change is needed;
- compatibility impact;
- migration path;
- ownership.

## Prohibited Shortcuts

- no silent partial persistence;
- no naive persisted datetimes;
- no hidden missing-data substitution;
- no domain-to-CLI imports;
- no History dependency on live analysis;
- no overwriting immutable archives;
- no provider-output bypass around grounding validation;
- no production bypass around required governance/budget controls;
- no mass refactoring without focused reason and regression coverage;
- no autonomous portfolio mutation or broker execution without an explicit future contract.
