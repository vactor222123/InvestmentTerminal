# Phase 6 — Integrated Investment Review Workflow Boundary Audit

## Verified baseline

`develop @ 89c3a706cd425c0fbe85e5321c841d297a2260ee`

## Audit scope

This audit covers the Phase 6 roadmap flow:

```text
refresh data
→ validate evidence
→ analyze portfolio
→ analyze market
→ generate Review Package
→ archive history
→ compare changes
→ produce investment review
```

The audit is limited to composition, authority, failure, and handoff
boundaries. It does not reopen completed analytical algorithms, provider
adapters, or persistence internals from Phases 1–5.

## Existing capabilities

| Workflow responsibility | Existing owner and evidence | Audit conclusion |
|---|---|---|
| Refresh and validate current stock data | `MarketDataRefreshService`, current-state analysis services, and `portfolio_ranking` composition | Implemented, but not composed into one review run |
| Analyze current portfolio | Portfolio snapshot, market value, policy-gap, contribution, lifecycle, performance, risk, and strategy-rule services | Implemented as independent evidence boundaries |
| Analyze the market | Current-state equity analysis plus Phase 5 maintained-universe, ETF discovery, sector analysis, and screening services | Implemented, but Phase 5 evidence is not connected to the Review Package |
| Generate Review Package | `InvestmentReviewPackageBuilder`, review adapters, exporter, and `investment_review_package` CLI | Implemented; legacy CLI still emits explicit `NOT_CONNECTED` sections |
| Preserve immutable history | `HistoricalSnapshotService` and `archive_review_package` CLI | Implemented with archive/manifest rollback semantics |
| Build queryable History | `HistoricalManifestImportService`, `HistoricalImportPipeline`, and `import_history` CLI | Implemented as an explicit rebuildable projection |
| Compare changes | `HistoricalSnapshotComparisonService` and `compare_history` CLI | Implemented for two explicitly selected imported snapshots |
| Produce AI-assisted interpretation | Knowledge and grounded-AI application boundaries | Implemented downstream, but automatic History-to-Knowledge promotion is deliberately forbidden |

## Boundary gaps

There is no single application-level run contract that records which stages
were requested, completed, skipped, or failed. The existing
`prepare_review_package_history_handoff` function is deliberately side-effect
free and only preserves the Review-to-History authority boundary; it is not a
workflow coordinator.

The current CLI surface requires separate commands for package generation,
archive registration, History import, and comparison. Consequently there is no
single run identity, deterministic stage report, or fail-closed rule preventing
later stages after an earlier required stage fails.

The Review Package contract predates several completed roadmap phases. Phase 4
external-context evidence has a lossless adapter, but the legacy package CLI
still writes `NOT_CONNECTED`. Phase 5 ETF discovery, sector evidence, and
screening are not yet composed into the package. Portfolio lifecycle and risk
evidence also remain separate from the legacy CLI path. Connecting these inputs
requires explicit adapters and missing-evidence accounting; it must not be
implemented as loosely shared dictionaries inside an orchestration command.

History archiving and SQLite import are distinct authority steps. The workflow
may coordinate them, but must not treat a successful archive as a successful
projection import, and must never make SQLite the historical source of truth.
Comparison requires an earlier compatible imported snapshot; a first run must
report comparison as unavailable rather than inventing a zero-change baseline.

Grounded AI is downstream of verified Knowledge. Phase 6 must not automatically
promote a newly archived Review Package into Knowledge or send raw workflow
state directly to a provider. Producing the deterministic investment-review
artifact and requesting grounded interpretation must remain separately visible
actions.

## Required authority and failure rules

```text
provider/infrastructure refresh
→ validated domain evidence
→ deterministic analysis
→ Review Package
→ immutable archive + manifest
→ rebuildable History projection
→ compatible historical comparison
→ optional explicit downstream interpretation
```

- Orchestration owns sequencing and reporting, not analytical calculations.
- Required stage failure stops dependent stages and remains visible.
- Optional missing evidence remains explicit and never becomes confident data.
- Review Package export must complete before archival begins.
- Archive registration is the point where canonical historical evidence exists.
- Projection/import failure must not rewrite a registered archive.
- Comparison is read-only and may only use compatible imported snapshots.
- Re-running a workflow must not silently duplicate immutable evidence.
- No Phase 6 boundary grants human-decision or trade-execution authority.

## Smallest implementation sequence

1. **Package 1 — Workflow run contract — COMPLETE.** Add immutable, versioned stage and run
   result models with `COMPLETED`, `SKIPPED`, and `FAILED` outcomes, explicit
   dependencies, run time, warnings, and artifact identities without changing
   Review Package JSON.
2. **Package 2 — Deterministic evidence assembly — COMPLETE.** Compose existing current
   portfolio, current-state market, Phase 4 context, and Phase 5 discovery
   evidence through typed adapters with explicit missing coverage.
3. **Package 3 — Review generation/export stage — COMPLETE.** Generate and atomically export
   one Review Package from assembled evidence.
4. **Package 4 — History preservation/projection stage — COMPLETE.** Coordinate
   existing archive and import services while reporting their outcomes
   separately. A projection failure preserves and identifies the registered
   canonical archive instead of rolling it back or reporting complete success.
5. **Package 5 — Historical comparison stage.** Select the previous compatible
   snapshot deterministically and expose first-run/unavailable states.
6. **Package 6 — User-facing workflow command.** Add `investment-terminal review`
   after the application contract is stable, with a hermetic end-to-end test and
   no automatic AI or trade execution.
7. **Phase closure audit.** Verify the complete roadmap flow and architecture.

## Audit decision

Phase 6 does not require redesign of Review, History, Knowledge, or completed
analysis domains. It requires a thin application orchestration layer that
composes their public boundaries and makes partial progress and failures
explicit.

The next action is **Phase 6 Package 5 — Historical comparison stage**.
