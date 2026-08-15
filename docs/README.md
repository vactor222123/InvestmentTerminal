# Investment Terminal Documentation

Investment Terminal is a private, local-first investment intelligence platform
built around deterministic analysis, preserved evidence, traceable Knowledge,
evidence-grounded AI, and explicit operational accounting.

## Documentation Authority

Canonical repository-level authority lives at the root:

```text
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
README.md
CHANGELOG.md
```

The `docs/` directory contains supporting synchronized architecture,
domain-context, operational, and historical material.

If a `docs/` file conflicts with a canonical root document, the root document
is authoritative.

## Current Product State

```text
Sprint 30 CLOSED
Sprint 31 — Evidence Integrity & Delivery Hardening — IN PROGRESS
```

Current authority flow:

```text
Review Package
→ immutable History
→ explicit verified ingestion
→ Knowledge
→ Grounded AI
→ grounding validation
→ ADMISSIBLE generated evidence
→ durable grounded-generation persistence
```

Provider usage/cost accounting is parallel operational accounting, not
investment authority.

## Production Surface

```text
GET  /health
GET  /ready
POST /v1/grounded-ai
GET  /v1/grounded-generations?limit=<N>
GET  /v1/grounded-generations/{request_id}
GET  /openapi.json
```

Readiness covers:

```text
knowledge_database
provider_usage_cost_database
grounded_generation_database
provider_credentials
```

## Operational CLIs

```text
python -m investment_terminal.cli.provider_usage_cost
python -m investment_terminal.cli.grounded_generations
```

Historical and Knowledge workflows remain exposed through their dedicated CLIs.

## Sprint 31 Hardening

Completed:

- deep immutability for persisted grounded generation JSON;
- strict JSON persistence rules;
- expanded executable architecture dependency guards.

Next hardening work targets reproducible dependencies and automated CI gates.

## Testing

```powershell
python -m pytest -q
```
