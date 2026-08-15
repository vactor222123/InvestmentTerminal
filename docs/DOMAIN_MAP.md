# Investment Terminal — Domain Map

**Status:** Canonical Architecture Map  
**Updated after:** Post-Sprint-26 Audit Fix 1  
**Baseline:** `develop @ ad9dd1f`

## 1. High-Level Map

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

Supporting boundaries:

```text
Configuration · Infrastructure · Persistence · Serialization · CLI · HTTP · Provider Transport · Logging
```

## 2. Domain Maturity

| Domain / Boundary | Status |
|---|---|
| Market / External Data | Established |
| Technical Analysis | Established |
| Fundamental Analysis | Established |
| Ranking / Recommendation | Established |
| Portfolio | Established |
| Decision | Established / evolving |
| Review | Established |
| History | Established |
| Historical Intelligence | Established |
| Outcome Research | Established descriptive foundation |
| Knowledge | Established |
| Grounded AI | Established |
| Provider Integration | Established OpenAI implementation |
| Provider Governance / Usage / Budgets | Established |
| Application / API | Established |
| Production Server | Established |
| Inbound Authentication / Request Limits | Established |
| Inbound Rate Limiting | Established, process-local |
| Broker Execution | Not implemented / intentionally out of scope |

## 3. Review

Owns the versioned Review Package and assembly of completed analytical outputs.

Does not own analytical calculations or historical storage.

## 4. History

Owns:

- immutable exact-byte archive;
- snapshot metadata;
- append-only manifest;
- checksum/path verification;
- SQLite schema/migrations;
- explicit import state;
- structured import;
- timeline persistence;
- typed repositories;
- verified archived package loading.

Canonical evidence remains archived JSON. SQLite is rebuildable.

## 5. Historical Intelligence / Outcome Research

Owns:

- compatibility;
- comparison;
- replay;
- outcome observations;
- descriptive outcome research;
- methodology identity;
- provenance/population-quality assessment.

Consumes verified History. Does not rewrite it.

## 6. Knowledge

Owns versioned, traceable Knowledge records and evidence references derived from verified sources.

Knowledge is rebuildable and cannot mutate History.

## 7. Grounded AI

Owns:

- grounded prompt contracts;
- deterministic Knowledge context selection;
- provider-neutral model-response contracts;
- strict response parsing;
- grounding validation;
- grounded generation trace.

Provider output is untrusted before validation.

## 8. Provider Integration and Controls

Owns provider-transport composition and operational controls:

- credentials;
- provider/model governance;
- bounded retries;
- Retry-After handling;
- usage accounting;
- pricing/cost accounting;
- output-token limits;
- token/cost budgets.

Provider pricing is explicit configuration, not hardcoded provider truth.

## 9. Application / API

Owns provider-neutral application orchestration and stable API/error contracts.

```text
GroundedAIApplicationService
→ GroundedAIAPIAdapter
→ GroundedAIHTTPHandler
```

Does not own provider SDK details or domain persistence.

## 10. Production Server

Owns concrete runtime composition and HTTP transport concerns:

- FastAPI app;
- runtime configuration;
- readiness/liveness;
- inbound authentication;
- request-size guardrail;
- rate-limit enforcement;
- security headers;
- public OpenAPI;
- Uvicorn CLI.

Production provider governance, pricing, and budgets are wired through the canonical composition root.

## 11. Ownership Matrix

| Data / Capability | Owner |
|---|---|
| Review Package | Review |
| Historical snapshot/archive | History |
| Manifest | History |
| SQLite historical projection | History |
| Import state | History |
| Timeline event | History |
| Snapshot comparison/replay | Historical Intelligence |
| Outcome observation/research result | Outcome Research |
| Knowledge record | Knowledge |
| Evidence reference | Knowledge |
| Grounded prompt/result | Grounded AI |
| Provider usage/cost | Provider control layer |
| Application result/error | Application |
| HTTP response mapping | API/HTTP adapter |
| Server authentication | Production Server |
| Inbound rate-limit state | Production Server |
| Human investment decision | User |

## 12. Source-of-Truth Map

| Information | Source of Truth |
|---|---|
| Current portfolio | Portfolio Domain |
| Current Review Package | Review artifact |
| Historical Review Package | Immutable archived JSON |
| Snapshot metadata/index | Manifest / synchronized repository |
| Queryable historical projection | SQLite History |
| Historical comparison/replay interpretation | Historical Intelligence result |
| Knowledge | Versioned Knowledge record + evidence references |
| Grounded AI output | Validated grounded generation result, not historical evidence |
| Provider pricing used for accounting | Explicit runtime pricing configuration |
| Server rate-limit state | Process-local admission service |

## 13. Forbidden Dependencies

```text
History → live market API
History → current analysis calculations
Historical Intelligence → archive mutation
Knowledge → History mutation
Grounded AI → canonical historical rewrite
API/FastAPI → domain-rule ownership
CLI → domain-rule ownership
```

## 14. Intentional Runtime Constraint

Inbound rate-limit state is process-local.

Canonical production CLI therefore supports:

```text
--workers 1
```

until a future shared-state design is explicitly introduced.
