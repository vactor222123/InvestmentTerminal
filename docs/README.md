# Investment Terminal

> A private, local-first investment intelligence platform built around deterministic analysis, preserved evidence, traceable Knowledge, and evidence-grounded AI assistance.

**Status:** Active development  
**Latest completed milestone:** Sprint 26 — Inbound API Rate Limiting and Abuse Controls  
**Current phase:** Post-Sprint-26 audit closed; Sprint 27 planning ready  
**Primary language:** Python

## Overview

Investment Terminal is a modular monolith for long-term investment analysis and disciplined review workflows.

Established capability layers include:

```text
Current-State Analysis
→ Portfolio / Decision Intelligence
→ Review Package
→ Immutable History
→ Historical Intelligence / Outcome Research
→ Knowledge
→ Grounded AI
→ Application / API
→ Production Server
```

The central engineering rule is:

> Preserve verified evidence before interpretation, keep important calculations deterministic, and make conclusions traceable to their inputs.

## Current Production Surface

Canonical production factory:

```text
investment_terminal.server.production:create_app
```

Canonical CLI:

```powershell
python -m investment_terminal.cli.server
```

Runtime routes:

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /openapi.json
```

`/docs` and `/redoc` are disabled.

## Canonical Inbound Flow

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

Production currently supports one worker because inbound rate-limit state is process-local.

## Provider Controls

Canonical production composition includes:

- provider/model allowlisting;
- bounded retry/resilience;
- explicit output-token limit;
- total-token budget;
- total-cost budget;
- explicit provider pricing policy;
- usage/cost accounting;
- environment-backed provider credentials.

Economic controls are explicit runtime configuration. Provider pricing is not hardcoded as permanent truth.

## Historical Evidence

Canonical historical authority:

```text
Review Package
→ immutable archived JSON
→ append-only manifest
→ verified/rebuildable SQLite History
```

Archived JSON is canonical evidence. SQLite is a rebuildable query projection.

Historical comparison/replay and outcome research must consume verified evidence and may not rewrite archives.

## Knowledge and Grounded AI

Knowledge is an implemented versioned, traceable layer downstream of verified evidence.

Grounded AI flow:

```text
Knowledge
→ GroundedPromptInput
→ provider
→ untrusted response
→ strict parser
→ grounding validation
→ admissible grounded generation
```

Provider output is not canonical evidence.

## Main Engineering Principles

Investment Terminal prioritizes:

1. correctness;
2. determinism;
3. historical integrity;
4. explainability;
5. explicit ownership;
6. fail-closed security/governance;
7. maintainability;
8. focused changes;
9. production composition tests;
10. human decision ownership.

## Important Canonical Documentation

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/ARCHITECTURE.md
docs/DOMAIN_MAP.md
docs/AI_CONTEXT.md
docs/README.md
```

Historical sprint plans/reviews remain historical records rather than current architecture authority.

## Testing

Full suite:

```powershell
python -m pytest -q
```

Every focused change should retain a green full regression suite.

## Development Workflow

```text
focused audit
→ focused change
→ focused tests
→ full regression
→ inspect diff
→ one logical commit
```

Avoid broad refactors without a demonstrated problem.

## Post-Sprint-26 Independent Audit

Sprint 26 was followed by a full repository audit before Sprint 27.

Confirmed findings were remediated:

```text
AUD-001 / P1
Production provider budget/pricing composition
→ CLOSED at ad9dd1f

AUD-003 / P3
Canonical architecture/documentation drift
→ CLOSED at 5ec042d

AUD-002 / P3
Repository inventory drift
→ CLOSED at 3f2f56b
```

No confirmed audit finding remains open.

Current post-audit baseline:

```text
develop @ 3f2f56b
```

## Intentional Current Limitations

Not currently claimed:

- distributed/multi-worker rate-limit state;
- autonomous trading;
- broker execution;
- streaming grounded-AI responses;
- automatic provider pricing synchronization;
- persistent provider usage/cost ledger.

These are explicit future decisions, not hidden implementations.

## Current Phase

```text
Post-Sprint-26 audit CLOSED
Sprint 27 planning READY
```

Sprint 27 should begin only after a focused audit of the selected product boundary.

## Disclaimer

Investment Terminal supports investment research and portfolio review. It does not provide financial advice.

All investment decisions remain the responsibility of the investor.
