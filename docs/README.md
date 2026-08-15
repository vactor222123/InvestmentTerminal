# Investment Terminal

> A private, local-first investment intelligence platform built around deterministic analysis, preserved evidence, traceable Knowledge, and evidence-grounded AI assistance.

**Status:** Active development  
**Latest completed milestone:** Sprint 26 — Inbound API Rate Limiting and Abuse Controls  
**Current phase:** Post-Sprint-26 audit remediation  
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

## Repository Structure

High-level structure:

```text
InvestmentTerminal/
├── config/
├── data/
├── docs/
├── investment_terminal/
│   ├── ai/
│   ├── api/
│   ├── application/
│   ├── cli/
│   ├── history/
│   ├── knowledge/
│   ├── market_data/
│   ├── portfolio/
│   ├── review/
│   └── server/
├── tests/
├── Roadmap.md
└── requirements.txt
```

## Important Canonical Documentation

Current architecture/status authority:

```text
Roadmap.md
docs/PROJECT_STATUS.md
docs/ARCHITECTURE.md
docs/DOMAIN_MAP.md
docs/AI_CONTEXT.md
```

Historical sprint plans/reviews remain useful historical records but are not current architecture authority.

## Core Workflows

### Review / History

```text
Review Package
→ archive
→ manifest
→ verification
→ History import
→ timeline
→ comparison / replay / outcome research
```

Representative CLIs include:

```powershell
python -m investment_terminal.cli.investment_review_package
python -m investment_terminal.cli.archive_review_package
python -m investment_terminal.cli.import_history
python -m investment_terminal.cli.query_history
python -m investment_terminal.cli.compare_history
python -m investment_terminal.cli.replay_history
```

### Production Grounded AI Server

Configure runtime environment values, including:

```text
INVESTMENT_TERMINAL_KNOWLEDGE_DATABASE
INVESTMENT_TERMINAL_OPENAI_MODEL
INVESTMENT_TERMINAL_ALLOWED_OPENAI_MODELS
INVESTMENT_TERMINAL_PROVIDER_MAX_OUTPUT_TOKENS
INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_TOKENS
INVESTMENT_TERMINAL_PROVIDER_MAX_TOTAL_COST
INVESTMENT_TERMINAL_PROVIDER_BUDGET_CURRENCY
INVESTMENT_TERMINAL_PROVIDER_INPUT_COST_PER_MILLION_TOKENS
INVESTMENT_TERMINAL_PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS
INVESTMENT_TERMINAL_PROVIDER_PRICING_CURRENCY
INVESTMENT_TERMINAL_SERVER_API_KEY
INVESTMENT_TERMINAL_RATE_LIMIT_CAPACITY
INVESTMENT_TERMINAL_RATE_LIMIT_REFILL_TOKENS_PER_SECOND
```

Use `.env.example` as a shape/reference only. Replace provider pricing placeholders with current pricing for the configured model before production use.

## Installation

```powershell
git clone <repository-url>
cd InvestmentTerminal

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Testing

Full suite:

```powershell
python -m pytest -q
```

Focused test:

```powershell
python -m pytest tests\<test_file>.py -q
```

Every focused change should retain a green full regression suite.

## Development Workflow

```powershell
git checkout develop
git pull origin develop
```

Then:

```text
focused audit
→ focused change
→ focused tests
→ full regression
→ inspect diff
→ one logical commit
```

Avoid broad refactors without a demonstrated problem.

## Security and Privacy

Investment Terminal may process sensitive financial data.

Rules include:

- never commit credentials;
- keep inbound server credentials separate from provider credentials;
- validate archive paths before reads;
- preserve historical checksums and exact bytes;
- do not expose secrets in API/error/rate-limit metadata;
- keep provider responses untrusted until validation;
- keep budget/governance controls wired in canonical production composition;
- do not expose portfolio data without explicit user action.

## Intentional Current Limitations

Not currently claimed:

- distributed/multi-worker rate-limit state;
- autonomous trading;
- broker execution;
- streaming grounded-AI responses;
- automatic provider pricing synchronization;
- persistent provider usage/cost ledger.

These are explicit future decisions, not missing hidden implementations.

## Current Phase

Sprint 26 is complete.

A full repository audit after Sprint 26 found one production-critical composition gap: provider budget/pricing controls existed in lower layers but were not wired through the canonical production server path.

That gap is fixed at:

```text
ad9dd1f fix(server): enforce provider budgets in production
```

Remaining post-audit work is documentation/inventory reconciliation before Sprint 27 planning.

## Disclaimer

Investment Terminal supports investment research and portfolio review. It does not provide financial advice.

All investment decisions remain the responsibility of the investor.
