# Investment Terminal — Domain Map

**Status:** Supporting synchronized architecture map  
**Primary authority:** `Architecture.md` and `DataModel.md`

## High-Level Map

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

Parallel operational boundary:

```text
provider execution
→ provider usage/cost accounting
```

## Ownership Matrix

| Data / Capability | Owner |
|---|---|
| Review Package | Review |
| Historical archive/snapshot | History |
| Manifest | History |
| SQLite historical projection | History |
| Historical comparison/replay | Historical Intelligence |
| Outcome observations/research | Outcome Research |
| Knowledge record | Knowledge |
| Knowledge evidence reference | Knowledge |
| Grounded prompt/result | Grounded AI |
| Persisted grounded generation | Grounded AI generated-evidence persistence |
| Provider usage/cost record | Provider operational accounting |
| Application result/error | Application |
| HTTP response mapping | API/HTTP adapter |
| Authentication/rate-limit state | Production Server |
| Human investment decision | User |

## Source-of-Truth Map

| Information | Source of Truth |
|---|---|
| Current portfolio | Portfolio Domain |
| Current Review Package | Review artifact |
| Historical Review Package | Immutable archived JSON |
| Snapshot index | Manifest / synchronized repository |
| Queryable historical projection | SQLite History |
| Knowledge | Versioned Knowledge record + evidence references |
| Grounded AI output | Validated generation result |
| Persisted AI evidence | Grounded-generation store; not History/Knowledge |
| Provider pricing used for accounting | Explicit runtime pricing configuration |
| Provider usage/cost | Provider operational ledger |
| Server rate-limit state | Process-local admission service |

## Dependency Direction

Executable architecture guards enforce:

```text
History
→ no downstream Knowledge/AI/Application/API/Server imports

Knowledge
→ no AI/Application/API/Server imports

AI
→ may consume Knowledge
→ no History/Review/Application/API/Server/CLI imports

Application
→ may orchestrate AI/Knowledge
→ no Server/CLI/History-internal imports

API
→ may consume Application
→ no Server/CLI/History-internal imports

Server
→ may compose downstream runtime dependencies
→ no History-internal imports
```

## Runtime Constraint

Inbound rate-limit state remains process-local. Supported production execution
therefore remains single-worker until a shared-state limiter is explicitly
introduced.
