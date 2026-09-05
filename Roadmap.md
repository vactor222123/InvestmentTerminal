# Investment Terminal — Product Roadmap

**Status:** Canonical Roadmap  
**Updated after:** Sprint 31 — Evidence Integrity & Delivery Hardening  
**Current development branch:** `develop`

## Product Evolution

### Phase 7 Primary Product Outcome

Phase 7 prioritizes an automatically maintained factual dataset over
single-instrument metadata remediation. The user provides portfolio
transactions; the Terminal acquires and refreshes market data, calculates
deterministic indicators and portfolio performance, and exports evidence for a
separate ChatGPT analysis.

The working target is ten years of daily data. Delivery sequence:

1. audit the resumable batch-ingestion boundary;
2. qualify 10-20 instruments over ten years;
3. add a versioned maintained S&P 500 and representative ETF universe;
4. expand with bounded concurrency, retry, checkpoints, and failure isolation;
5. add incremental refresh and market-derived portfolio quotes;
6. export a compact ChatGPT-ready factual analysis bundle.

Recommendation expansion, autonomous conclusions, scheduling, mass execution,
and further single-ticker remediation are outside the immediate boundary.

The batch-ingestion audit is complete. The first implementation is a sequential
1-20 instrument service with an exact request checksum, private atomic
checkpoint, per-symbol failure isolation, and redacted aggregate report.
Ten-year live qualification follows implementation.
Package 57 implements that bounded sequential restart boundary. A controlled
10-20 instrument ten-year run and exact resume repeat are next.

The ten-year run and schema-2 resume are successful. Package 59 selects official
SPY daily fund holdings as the first automatic broad-US universe source while
explicitly avoiding an unsupported exact-index claim. Qualification precedes
any member-driven batch request.

Package 60 supersedes the unimplemented SPY source after clarifying that exact
S&P membership is unnecessary. Official Nasdaq Trader directories now define
the broad US-listed research universe; typed qualification precedes filtering
and candle-request generation.
Package 61 implements the bounded dual-file qualification. One live redacted
measurement is required before downstream eligibility or batch composition.

That live measurement succeeds with 12,424 unique accepted members. Package 62
selects a complete-universe resumable Yahoo eligibility scan instead of a
Nasdaq-venue liquidity shortcut. Package 63 implements its 90-day request,
private atomic checkpoint, redacted progress report, isolated outcomes, and
100-member invocation bound. Controlled private slices are next; ranking and
ten-year ingestion remain blocked until all members have terminal outcomes.

The first operational slice measures 10 successes and 90 undifferentiated
`APIError` failures. Package 64 audits the loss: yfinance's typed exceptions are
chained under one client `APIError`, while schema-1 persists only the outer type
and treats it as terminal. The next package adds privacy-safe causal categories,
atomic schema-1 migration, capped retry-pending outcomes, and immediate
rate-limit halt before any new universe members are attempted.

Package 65 implements that schema-2 boundary. It preserves terminal evidence,
migrates legacy generic failures to retry-pending, classifies live causal types
without provider text, prioritizes retries, caps attempts at three, and pauses
immediately on rate limiting. One controlled 10-attempt remediation measurement
is next; slice 002 and ten-year ingestion remain blocked.

Package 66 records that controlled measurement. Schema-1 migration preserved
all 100 outcomes, and 10 bounded retries resolved to eight `INVALID_RESPONSE`
and two `NO_PRICE_DATA` final outcomes without rate limiting. The remaining 80
legacy retry-pending outcomes must be drained in one bounded invocation before
slice 002 can be considered; ranking and ten-year ingestion remain blocked.

The retry drain resolves all 80 remaining legacy outcomes, producing 88
aggregate `INVALID_RESPONSE` and two `NO_PRICE_DATA` failures. Package 67 finds
that `INVALID_RESPONSE` collapses multiple client and service validation exits
and is terminal without a persisted subtype. Schema-3 typed diagnostics plus a
single final retry of those 88 outcomes is required before slice 002.

Package 68 implements schema-3 typed local validation categories and atomic
migration of the 88 eligible schema-2 invalid responses without resetting their
attempt counts. One controlled 10-attempt diagnostic measurement is next.

Package 69 records the complete diagnostic retry measurement: 10 successes,
86 numeric-response failures, two OHLC failures, and two no-price failures, with
no retry pending or rate-limit halt. The operator pauses further scanning and
Package 70 adds one automatic read-only raw-series diagnostic for the first
numeric failure. Its measurement returns 48 valid rows and no reproducible
defect. Package 71 audits the resulting stale-terminal risk and selects one
schema-4 production-client revalidation allowance for numeric failures only.
Package 72 implements that allowance with atomic schema-3 migration, a fourth
attempt only for `RESPONSE_NUMERIC`, schema-4 fail-closed validation, and no
change to any other retry cap. One controlled revalidation precedes slice 002.
That revalidation recovered one stale numeric outcome without rate limiting.
The remaining 85 numeric retries may now be drained in one bounded invocation;
its redacted result must be reviewed before slice 002.
The drain completed with 95 successes and five final failures across the first
100 members. Package 74 selects a separate budgeted coordinator over unchanged
100-item slices so the remaining 12,324 members can be processed automatically
with exact resume and immediate rate-limit stop. Implementation precedes the
complete-universe run.
Package 75 implements that coordinator and its redacted aggregate CLI. One
budgeted operational run is next.
Package 76 repairs resume validation for a fourth numeric attempt that ends in
a different terminal category. The unchanged checkpoint can now be resumed.
The resumed drain completed all 12,424 members with 12,020 successes and 404
isolated final failures. Package 77 selects a private, checksum-bound success
projection before currency policy, batch partitioning, or ten-year ingestion.
Package 78 implements that fail-closed private projection and its separate
aggregate-only report. One controlled projection run is next; currency policy,
batch construction, and ingestion remain blocked until its report is reviewed.
The controlled projection is successful: 12,020 of 12,424 terminal members are
included and 404 are explicitly excluded. Package 79 records the checksum-bound
result. A focused currency and batch-construction audit is next; ingestion
remains blocked.
Package 80 verifies that neither Nasdaq source evidence nor eligibility success
proves currency, while the current batch and candle contracts require it before
persistence. It selects a separate bounded resumable exact-symbol Yahoo currency
qualification. Batch generation and ingestion remain blocked until that
contract is implemented and measured.
Package 81 implements the bounded resumable exact-symbol currency boundary with
private atomic evidence, capped retry semantics, immediate rate-limit stop, and
an aggregate-only report. One controlled item must be reviewed before a larger
currency slice or any batch generation.
The first controlled item returned terminal `INVALID_CURRENCY` without rate
limiting. Package 82 records the result and blocks broader scanning. A separate
single-outcome redacted diagnostic must distinguish the currency-field shape
before the contract or provider surface is changed.
Package 83 implements that single-outcome read-only diagnostic with checksum
validation and aggregate-only field-shape evidence. Its controlled result must
be reviewed before changing the provider surface or resuming currency scans.
The diagnostic confirms the exact Yahoo Search row omits currency. Package 84
records that result and selects one fail-closed chart-metadata currency
qualification before any broader scan or batch generation.
Package 85 implements that one-symbol chart-metadata qualification with separate
private evidence and an aggregate-only report. Its controlled result is next.
That result succeeds. Package 86 records the evidence and selects versioned
resumable integration: reopen only `INVALID_CURRENCY` and use chart metadata
directly for new pending symbols before any batch construction.
Package 87 implements schema-version-2 resumable integration. Migration is
checkpointed before provider access, only `INVALID_CURRENCY` is reopened, and
all subsequent pending symbols use chart metadata under the existing bounded
retry and rate-limit controls. One controlled item is next; batch construction
and candle ingestion remain blocked pending its redacted result.
The first schema-version-2 item succeeds through chart metadata with no failure
or rate-limit halt. Package 88 records the result and authorizes one bounded
100-item currency slice. A complete drain, batch construction, and candle
ingestion remain blocked until that aggregate result is reviewed.
The controlled 100-item slice then qualifies all 100 attempted items without
failure, retry, or rate limiting, for 101 cumulative successes. Package 89
records the result and selects an audit of a bounded resumable complete-drain
coordinator so the operator does not manually repeat roughly 120 invocations.
No complete run, batch construction, or ingestion is yet authorized.
Package 90 audits the complete chart-currency drain boundary and selects a
separate coordinator over unchanged 100-item slices. It must enforce a bounded
total budget, preserve atomic exact resume, stop on completion, rate limiting,
failure, or zero progress, and emit only aggregate evidence. Implementation and
tests precede any complete live run.
Package 91 implements that separate coordinator and CLI with a maximum 20,000
item run budget, unchanged 100-item slices, exact checkpoint carry-forward,
completion/rate-limit/budget/zero-progress stops, exact completed resume, and
aggregate-only reporting. One explicitly bounded live run is next; batch
construction and ingestion remain blocked pending its result.
The bounded live drain completes terminal currency evidence for all 12,020
members: 12,019 successes and one isolated `INVALID_RESPONSE`, with no pending
or never-attempted members and no rate-limit halt. Package 92 records this
result. An exact completed resume must demonstrate zero provider work before
the batch-construction boundary is audited.
The exact repeat then returns `COMPLETE` with zero attempted items and zero
provider requests while preserving all terminal coverage. Package 93 records
the idempotency evidence. Package 94 audits deterministic success-only batch
construction and selects an offline checksum-bound private manifest. Existing
requests already carry per-symbol currencies and cap each request at 20 items;
12,019 successes therefore map to 601 requests while the one terminal failure
remains excluded. Manifest implementation precedes any ingestion.
Package 95 implements the offline manifest service and CLI with exact evidence
binding, success-only inclusion, deterministic 20-item partitions, per-request
checksums, atomic private output, and a separate redacted report. One controlled
private construction is next; batch execution remains blocked.
The controlled construction succeeds: all 12,020 members are accounted for,
12,019 successful outcomes form 601 bounded requests, and one terminal failure
remains excluded. Package 96 records the checksum-bound result. Audit a smallest
measurable execution slice next; complete-manifest ingestion remains blocked.
Package 97 confirms that the existing one-request executor is bounded and
resumable but its report cannot prove manifest provenance. A separate
manifest-bound one-batch executor with manifest/index/request checksums is the
next implementation. No batch execution is authorized by the audit.
Package 98 implements that one-batch manifest binding while reusing existing
request validation, checkpoint, ingestion, and aggregate accounting. One
controlled batch-index-1 run is next; no later index or manifest drain is yet
authorized.

```text
Foundation
→ Current-State Analysis
→ Portfolio and Decision Intelligence
→ Unified Review Package
→ Historical Intelligence
→ Knowledge Domain
→ Evidence-Grounded AI
→ Provider Governance and Resilience
→ Production API Runtime
→ Inbound Abuse Controls
→ Explicit History-to-Knowledge Ingestion
→ Persistent Provider Usage & Cost Accounting
→ Provider Operational Accounting Hardening
→ Persistent Grounded Generation Evidence
→ Evidence Integrity & Reproducible Delivery
```

## Recent Completed Milestones

### Sprint 27 — Explicit History-to-Knowledge Ingestion

Verified deterministic History → Knowledge ingestion, exact evidence/checksum
preservation, idempotent immutable versions, dry-run validation, and real E2E.

### Sprint 28 — Persistent Provider Usage & Cost Ledger

Added immutable provider-neutral usage/cost accounting with dedicated SQLite
persistence and operational CLI.

### Sprint 29 — Provider Operational Accounting Hardening

Added runtime-configured ledger path, schema-aware readiness, bounded queries,
exact Decimal summary aggregation, connection lifecycle hardening, and real
operational E2E.

### Sprint 30 — Grounded Generation Persistence & History

Added immutable generated-evidence persistence, runtime composition, readiness,
bounded queries, CLI/HTTP inspection, and real durable Knowledge → generation →
persistence → reopen/readback E2E.

### Sprint 31 — Evidence Integrity & Delivery Hardening

Delivered:

- true deep immutability for persisted grounded generation/trace JSON;
- strict JSON value validation;
- fail-closed rejection of non-finite numbers and non-string object keys;
- detached serialization and strict SQLite JSON persistence;
- expanded executable architecture dependency/authority guards;
- explicit documentation authority hierarchy;
- complete environment contract for grounded-generation persistence;
- Python 3.13.x dependency-resolution baseline;
- separate runtime/dev dependency source manifests;
- pinned dependency compiler toolchain;
- hash-locked runtime and development dependency artifacts;
- cross-platform dependency ownership without hidden `fastapi[standard]` extras;
- first GitHub Actions quality gate;
- locked Linux CI installation;
- dependency and architecture contract checks in CI;
- full regression suite in CI;
- whitespace gate;
- hermetic portfolio/review tests that no longer depend on a developer-local
  personal portfolio file.

Sprint 31 closes with both local and clean Linux CI regression suites green.

## Stable Authority Hierarchy

```text
Archived Review Package
→ History
→ explicit verified History-to-Knowledge ingestion
→ Knowledge
→ GroundedPromptInput
→ provider execution
→ grounding validation
→ ADMISSIBLE GroundedGenerationResult
→ persisted grounded generation evidence
```

Generated evidence remains downstream and is not automatically promoted into
History or Knowledge.

Parallel operational accounting remains:

```text
successful priced provider usage
→ immutable provider usage/cost ledger
→ bounded operational queries / exact summaries
```

## Delivery Integrity Baseline

Repository delivery now includes:

```text
Python 3.13.x
→ declared direct dependencies
→ pinned resolver/compiler toolchain
→ hash-locked dependency artifacts
→ clean Linux CI install
→ architecture contract tests
→ full pytest
→ git diff --check
```

Canonical CI workflow:

```text
.github/workflows/ci.yml
```

## Deferred Scope

Still deferred:

- automatic/scheduled History-to-Knowledge ingestion;
- shared/distributed rate-limit state;
- deployment container/image and infrastructure manifests;
- scheduled backup/restore drills and measured recovery objectives;
- TLS termination/HSTS deployment policy;
- authorization beyond API-key authentication;
- retry jitter;
- proactive/concurrency-aware provider throttling;
- streaming responses;
- additional provider adapters;
- provider pricing synchronization;
- semantic entailment/contradiction detection;
- vector retrieval/embeddings;
- generated-evidence promotion governance;
- autonomous portfolio actions;
- broker execution.

## Current Decision Point

Phases 1–6 of the post-audit product roadmap are complete. The Phase 6
Integrated Investment Review Workflow boundary audit is recorded in
`docs/PHASE_6_WORKFLOW_BOUNDARY_AUDIT.md` at verified baseline
`89c3a706cd425c0fbe85e5321c841d297a2260ee`. Packages 1–6 now establish the
workflow contract, typed evidence aggregate, atomic Review export, and the
separate canonical History preservation, rebuildable projection, and
deterministic historical comparison stages plus the user-facing command.

Next:

```text
Phase 6 Package 1 — immutable workflow run contract — COMPLETE
→ Phase 6 Package 2 — typed evidence assembly — COMPLETE
→ Phase 6 Package 3 — Review export — COMPLETE
→ Phase 6 Package 4 — History preservation/projection — COMPLETE
→ Phase 6 Package 5 — historical comparison — COMPLETE
→ Phase 6 Package 6 — user-facing review command — COMPLETE
→ initial Phase 6 closure audit — REMEDIATION REQUIRED
→ failure-reporting remediation — COMPLETE
→ repeat Phase 6 closure audit — COMPLETE
→ Phase 7 Operational Data and First Real Use boundary audit — COMPLETE
→ Phase 7 Package 1 operational data baseline and coverage report — COMPLETE
→ first local operational baseline — COMPLETE: no populated real inputs found
→ Phase 7 Package 2 Yahoo Historical Candle Operational Qualification — IMPLEMENTED
→ yfinance runtime cache remediation — COMPLETE
→ bounded Yahoo qualification — SUCCESS (MSFT, 12 daily candles)
→ Phase 7 Package 3 bounded Yahoo candle ingestion — COMPLETE
→ Package 3 live persistence and idempotency verification — COMPLETE
→ Phase 7 Package 4 stored coverage measurement — COMPLETE
→ controlled one-year MSFT ingestion — COMPLETE (251 daily candles)
→ Phase 7 Package 5 explicit-session coverage quality — COMPLETE
→ bounded one-year XNAS session evidence — COMPLETE
→ controlled five-year MSFT/XNAS coverage — COMPLETE (1,254/1,254 sessions)
→ controlled second XNAS instrument (AAPL) — COMPLETE (1,254/1,254 sessions)
→ bounded official XNYS session evidence — COMPLETE
→ generate and verify XNYS@1 — COMPLETE (workspace-staged)
→ bounded IBM Yahoo qualification — SUCCESS (1,254 daily candles)
→ controlled IBM/XNYS ingestion, repeat, and coverage — COMPLETE (1,254/1,254 sessions)
→ focused measured-state audit — COMPLETE (3,762 candles; freshness unmeasured)
→ bounded single-instrument refresh observability — COMPLETE
→ one live MSFT stale-to-fresh measurement — COMPLETE (4 inserted)
→ exact already-fresh MSFT repeat — COMPLETE (provider bypassed)
→ audit refresh-report projection into operational baseline — COMPLETE
→ optional backward-compatible refresh-report projection — COMPLETE
→ focused Phase 7 closure-readiness audit — COMPLETE: NOT READY
→ current-portfolio operational input audit — COMPLETE
→ controlled current-portfolio runtime qualification — COMPLETE
→ portfolio-transaction operational input audit — COMPLETE
→ bounded transaction CSV qualification — COMPLETE
→ controlled private transaction CSV qualification — COMPLETE (62 events)
→ atomic transaction batch-import audit — COMPLETE
→ atomic repository batch-append boundary — COMPLETE
→ bounded durable transaction-import CLI/report audit — COMPLETE
→ bounded durable transaction-import CLI/report — COMPLETE
→ controlled private transaction import — COMPLETE (62/62 inserted)
→ exact-repeat private transaction import — COMPLETE (0 inserted, 62 duplicates)
→ transaction-derived valuation operational audit — COMPLETE
→ bounded transaction-derived valuation CLI/report — COMPLETE
→ offline quote qualification audit — COMPLETE
→ bounded offline quote qualification CLI/report — COMPLETE
→ controlled private offline quote qualification — COMPLETE: BLOCKED
→ transaction instrument-metadata enrichment audit — COMPLETE
→ bounded provenance-aware instrument-metadata enrichment — COMPLETE
→ automated instrument-metadata bootstrap audit — COMPLETE
→ bounded OpenFIGI v3 metadata bootstrap — COMPLETE
→ controlled private OpenFIGI metadata bootstrap — COMPLETE: BLOCKED
→ privacy-safe OpenFIGI failure categorization — COMPLETE
→ categorized controlled private OpenFIGI bootstrap — COMPLETE: BLOCKED
→ split privacy-safe OpenFIGI ticker categories — COMPLETE
→ schema-3 controlled private OpenFIGI bootstrap — COMPLETE: BLOCKED
→ deterministic candidate-ticker row filtering — COMPLETE
→ filtered controlled private OpenFIGI bootstrap — COMPLETE: BLOCKED
→ local-only candidate-absence diagnostic audit — COMPLETE
→ bounded local-only candidate-absence diagnostic — COMPLETE
→ controlled diagnostic-producing OpenFIGI rerun — COMPLETE: BLOCKED
→ local candidate-absence evidence review — COMPLETE: REVIEW REQUIRED
→ automated private ticker-resolution audit — COMPLETE
→ bounded Yahoo ISIN-search qualification — COMPLETE
→ controlled private Yahoo ISIN-search measurement — NEXT
→ Phase 8 User Product Layer — DEFERRED UNTIL REAL OPERATIONAL GAPS ARE MEASURED
```

Phase 7 turns existing architecture into a populated and measured product. It
must separately report architecture capability, configured provider capability,
actual populated coverage, measured runtime performance, deterministic evidence,
and AI/human interpretation. Approximately 20-year candle coverage and an
approximately 1000-company universe remain targets, not current-state claims.

The canonical Phase 7 boundary audit is
`docs/PHASE_7_OPERATIONAL_DATA_BOUNDARY_AUDIT.md`. The previous UI scope is now
Phase 8 and remains non-executing, explicit-action, evidence-visible, and
read-only at broker boundaries.

Phase 7 Package 54 adds fail-closed exact Yahoo ticker-match qualification
after the successful bounded ISIN-search measurement. Runtime mutation remains
deferred until the private match result is reviewed.

## Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes locally;
- clean CI regression suite passes;
- architecture boundaries remain clean;
- dependency installation is reproducible;
- documentation reflects implementation;
- deferred scope is explicit;
- repository inventory is reconciled;
- repository is committed and pushed.
