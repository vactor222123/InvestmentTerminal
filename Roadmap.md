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
