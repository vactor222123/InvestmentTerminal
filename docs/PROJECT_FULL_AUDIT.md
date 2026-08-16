# InvestmentTerminal — Full Product Alignment Audit

**Repository:** `vactor222123/InvestmentTerminal`  
**Branch audited:** `develop`  
**HEAD audited:** `191b6ee` — `docs: close sprint 33 current state intelligence`  
**Audit mode:** Product alignment audit; no application code changed.

## 1. Executive summary

InvestmentTerminal is a coherent, well-tested modular monolith with unusually
strong foundations for evidence preservation, historical integrity, grounded AI
boundaries, operational SQLite management, and deterministic stock-oriented
current-state analysis. It already supports a meaningful path from configured
equity universe through refreshed market/fundamental data, technical and
fundamental scoring, ranking, recommendations, a Review Package, and explicit
History handoff.

It is not yet the complete personal investment operating system defined in
`PROJECT_VISION.md`. The main gap is not generic architecture: it is product
coverage. The system remains principally a configured-US-equity analysis and
review platform, rather than a broad multi-asset portfolio and discovery
platform. ETF intelligence, transaction-led portfolio history, complete risk
analysis, macro/news context ingestion, large-universe discovery, broker
integration, and a user-facing application remain absent.

The existing architecture is suitable for the next product phases provided
those capabilities are added through the established data → deterministic
analysis → Review Package → History → Knowledge boundaries.

## 2. Current maturity assessment

| Dimension | Maturity | Assessment |
|---|---|---|
| Evidence integrity and History | High | Immutable exact-byte archives, manifest, checksum verification, confined paths, migrations, atomic imports, replay, comparison, and outcome research are implemented. |
| Current-state stock analysis | Medium-high | A canonical typed workflow exists for configured equity universes and fails closed on non-ready daily market data. |
| Portfolio intelligence | Medium | Holdings, sleeves, strategic policy gaps, market values, contribution plans, deployment evidence, and portfolio audits exist; transaction history and broader risk management do not. |
| Knowledge and grounded AI | High foundation | Explicit verified History-to-Knowledge ingestion, provenance, grounding validation, provider governance/accounting, and durable generated evidence exist. |
| Production operations | Medium-high | Runtime filesystem contracts, backup/restore, container baseline, FastAPI lifecycle, authentication, request limits, and single-worker rate limiting are implemented. |
| Product breadth | Early | The intended ETF, macro, news, discovery, broker, and desktop/UI capabilities are mostly deferred. |

## 3. Architecture overview

The implementation follows the documented authority flow:

```text
market/external providers
→ deterministic analysis
→ Review Package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ grounded generation and validation
→ durable generated evidence
```

### Observed structure and boundaries

- `clients`, `market`, `services`, `indicators`, `decision_engine`, and
  `portfolio` own external acquisition and deterministic calculations.
- `review` adapts calculated outputs into the versioned Review Package; it does
  not recalculate ranking or scoring.
- `history` owns archive, manifest, migrations, import state, normalized SQLite
  projection, comparison, replay, and outcome-research components.
- `knowledge` owns versioned records and evidence references. History-to-
  Knowledge ingestion is explicit and verified.
- `ai`, `application`, `api`, and `server` form distinct grounded-generation,
  application, HTTP, and production-runtime layers. Executable dependency tests
  enforce this direction.
- `persistence` and server runtime services keep operational/provider/grounded
  generation SQLite stores separate from canonical archived history.

This supports the long-term vision well. The main architectural risk is not a
wrong dependency direction, but extending a stock-oriented current-state
pipeline into ETFs, funds, non-US instruments, macro/news, and discovery
without first defining the necessary source and normalization contracts.

## 4. Product vision alignment matrix

| Area | Status | Notes |
|---|---|---|
| Market price ingestion | Partially implemented | Finnhub and Yahoo clients exist; current canonical analysis uses Yahoo historical OHLCV. |
| Fundamental ingestion | Partially implemented | Yahoo fundamental snapshots, quality assessment, sector-aware scoring, and bank policies exist. |
| Data normalization and freshness | Implemented | Typed candles/fundamentals, validation, quality signals, and US-session-aware daily freshness checks exist. |
| 20-year historical market database | Missing | Candles can be stored, but no governed bulk backfill, coverage catalogue, retention policy, or multi-decade data programme exists. |
| Technical analysis | Partially implemented | Moving averages, momentum, volatility, technical scoring, and candle analysis exist; chart-pattern recognition is absent. |
| Fundamental/valuation analysis | Partially implemented | Broad metric normalization and scoring exist; coverage is provider-dependent and ETF/fund analysis is absent. |
| Ranking and recommendations | Implemented | Deterministic ranking, coverage-aware recommendations, theses, allocation, and decision models are present. |
| Confidence/evidence model | Partially implemented | Data quality, freshness, provenance, coverage, and grounding safeguards exist; the complete product confidence decomposition remains incomplete. |
| Current-state workflow | Implemented | Sprint 33 provides configured universe → analysis → typed result → Review Package → explicit History handoff. |
| Portfolio representation | Implemented | Holdings, ISIN/ticker identity, cost basis, sleeves, strategies, policy, cash, imports, and audit models exist. |
| Strategic allocation/contributions | Implemented | Core/tactical/reserve policy, policy-gap calculation, allocation constraints, and contribution planning exist. |
| Portfolio transactions and performance history | Missing | No transaction ledger, realised/unrealised performance model, tax lots, or time-series portfolio valuation ledger was found. |
| Risk/rebalancing | Partially implemented | Allocation limits and policy gaps exist; risk budget, drawdown, correlation, volatility-at-portfolio level, and executable rebalancing proposals are not established. |
| Review Package | Implemented | Versioned Review Package models/builders/exporters and typed current-state composition exist. Some generic sections are placeholders for future intelligence. |
| Immutable History | Implemented | Archive, manifest, integrity checks, atomic normalized import, timeline, comparison, replay, migration, and recovery state are implemented. |
| Outcome research | Partially implemented | Outcome observation, methodology, cohorts, population/provenance controls, and research query paths exist; it remains evidence research, not predictive learning. |
| History-to-Knowledge | Implemented | Explicit verified, traceable ingestion and versioned Knowledge records exist. |
| AI evidence boundary | Implemented | Provider output is parsed, grounded against Knowledge, validated fail-closed, and stored downstream only when admissible. |
| External news/macro/geopolitical context | Missing | Architecture and AI boundary support it, but no ingestion, normalization, provenance, or Review Package context implementation exists. |
| ETF intelligence | Missing | ETFs are supported as portfolio holding types, but ETF characteristics, look-through/risk analysis, and ETF discovery are absent. |
| Market discovery at scale | Missing | Text-file configured universes and sequential analysis exist; no maintained broad universe catalogue, screening pipeline, or scalable discovery workflow exists. |
| Windows/desktop UI | Missing | CLI, JSON, and HTTP API boundaries provide a foundation, but no Windows application or portfolio-management UI exists. |
| Broker/Trade Republic integration | Missing | Explicitly outside current scope; no broker adapter, transaction import, or execution capability exists. |
| Production runtime and recovery | Implemented | FastAPI, API-key authentication, request limits, rate limiting, runtime filesystem, backup/restore, container baseline, and CI contracts exist. |

## 5. Critical gaps

1. **Multi-asset data model and analysis coverage.** The vision requires ETFs,
   bonds, defensive assets, and broad-market instruments. Current canonical
   live analysis is explicitly equity-focused; ETF intelligence is deferred.
2. **Portfolio transaction and performance history.** Current holdings and cost
   basis support a snapshot, not an auditable lifecycle of purchases, sales,
   dividends, fees, tax lots, or realised performance.
3. **External context platform.** No governed data contracts exist for news,
   macroeconomic, event, or geopolitical evidence, despite these being central
   to the intended AI-assisted review.
4. **Market discovery and scalable universe management.** Configured text
   universes are appropriate for the present workflow but do not discover or
   maintain thousands of assets.
5. **Integrated review command.** Sprint 33 establishes a current-state path,
   but the mature one-command workflow described by the vision is not yet an
   end-to-end product workflow across portfolio, universe, review, history,
   and context.
6. **Human-facing portfolio experience.** No desktop/UI layer exists for
   ordinary portfolio operations, explanation, approvals, or review navigation.

## 6. Technical risks

- **Provider dependence:** current live market and fundamental workflows rely
  principally on Yahoo Finance, with Finnhub available for quote/candle paths.
  There is no source-quality/fallback policy across the full product surface.
- **US-market assumption:** daily freshness uses a US equity calendar. This is
  correct for the implemented equity workflow but insufficient for global ETFs,
  exchanges, bonds, and other asset classes.
- **Sequential universe processing:** `UniverseAnalysisService` processes a
  configured universe one symbol at a time. This is deterministic and safe, but
  not an established large-universe operating model.
- **Float-heavy financial calculations:** existing validation and monetary
  rounding are careful, but several market/portfolio models use `float` rather
  than a comprehensive Decimal-led accounting model. This matters more once
  transactions, FX, tax, and performance accounting are introduced.
- **Documentation state drift:** `PROJECT_CONTINUATION.md` records Sprint 32 as
  current while HEAD closes Sprint 33; `docs/PROJECT_STATUS.md` and
  `docs/AI_CONTEXT.md` also lag the current baseline. These are handoff risks,
  not application failures.
- **Operational constraint:** the production limiter intentionally supports one
  worker because state is process-local. This is an explicit current limitation,
  not a defect under the documented contract.

## 7. Recommended development order

The sequence below is a product-alignment recommendation, not an implementation
plan.

1. Reconcile current handoff/status documentation with Sprint 33 and establish
   the product decisions for asset classes, supported exchanges, currencies, and
   data-source authority.
2. Build the multi-asset evidence foundation: ETF/fund/security identity,
   exchange/calendar/currency metadata, source provenance, and data-quality
   contracts.
3. Add transaction-led portfolio history and performance accounting before
   richer portfolio recommendation features.
4. Extend portfolio intelligence with portfolio-level risk, rebalancing
   evidence, and strategy-specific rules for core, long-term stocks, and
   position trades.
5. Establish a governed external-context domain for news, macro, events, and
   geopolitical evidence, then expose its explicit coverage/limitations in the
   Review Package.
6. Build scalable universe/discovery capability after data/source contracts and
   resource limits are defined.
7. Compose the validated pieces into the single review workflow envisioned by
   the product, preserving explicit archival and human-decision boundaries.
8. Add a Windows/UI experience only after stable portfolio and review contracts
   exist. Broker import can follow as a read-only data integration; execution
   remains outside the product’s non-goals.

## 8. Suggested future roadmap phases

### Phase A — Multi-asset evidence and portfolio accounting

ETF/fund contracts, exchange/currency/calendar support, transaction ledger,
portfolio valuation history, dividends/fees, and performance reporting.

### Phase B — Decision intelligence completion

Portfolio risk measures, rebalancing evidence, contribution-to-instrument
selection, strategy-specific risk/review rules, and explainable confidence
components.

### Phase C — Context and discovery intelligence

Provenanced news/macro/event context, market-regime evidence, maintained
universes, ETF/thematic analysis, and controlled broad-market discovery.

### Phase D — Integrated review operating workflow

One deterministic review orchestration across data refresh, quality checks,
portfolio analysis, review generation, explicit archive/import, comparison,
and operator-visible limitations.

### Phase E — User product and read-only integrations

Windows/desktop or web portfolio UI, review/history navigation, report
presentation, and carefully scoped read-only broker/import adapters. No
autonomous execution.

## 9. Testing and quality assessment

The repository contains **335 test files** covering domain models, boundary
contracts, architecture dependencies, persistence, history E2E, AI/provider
flows, server runtime, backup/restore, and Sprint 33 current-state workflow.
The test design uses injected providers and hermetic fixtures in many areas,
which is appropriate for deterministic CI.

The full suite was not executed in this audit environment because its Python
3.13.7 interpreter does not have `pytest` installed. The repository’s current
continuation document records the prior full regression result as `2190 passed,
3 skipped, 1 warning` for the Sprint 31 closure, and records green Sprint 32
local/CI validation. Those historical results are not treated as proof of the
current Sprint 33 HEAD.

Important future test priorities are therefore product contracts rather than
more isolated unit tests: multi-exchange freshness, multi-currency accounting,
transaction/performance lifecycle, ETF data provenance, external-context
provenance/freshness, broad-universe resource limits, and full integrated-review
workflow recovery behavior.

## Conclusion

The repository is architecture-ready for the InvestmentTerminal vision and is
already implemented beyond a prototype in its evidence, history, AI-boundary,
and operational foundations. The next phase should deliberately expand product
coverage, beginning with multi-asset evidence and transaction-led portfolio
history, rather than redesigning the established architecture or adding
ungoverned AI, broker execution, or user-interface surface prematurely.
