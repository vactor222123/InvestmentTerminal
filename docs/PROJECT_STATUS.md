# Project Status

## Repository

```text
vactor222123/InvestmentTerminal
branch: develop
```

## Current phase

```text
Sprint 14 — Outcome-Aware Historical Intelligence
```

## Completed foundations

- portfolio modelling and current portfolio workflows;
- market-data clients, repositories, freshness and refresh services;
- technical and fundamental analysis;
- decision, ranking, and recommendation flows;
- contribution and deployment planning;
- unified Review Package;
- immutable historical Review Package archive;
- append-only snapshot manifest;
- checksum, path-safety, encoding, schema, and timestamp identity validation;
- History SQLite schema with controlled migrations;
- explicit historical import state;
- atomic historical detail import;
- read-once verified historical byte contract;
- typed History repositories;
- historical timeline models and queries;
- snapshot navigation;
- snapshot compatibility assessment;
- portfolio-summary comparison;
- holdings comparison;
- recommendations comparison;
- deployment comparison;
- aggregate snapshot comparison;
- exact archived replay;
- normalized historical replay;
- read-only History query/comparison/replay CLIs;
- realistic deterministic History end-to-end fixture;
- Sprint 13 architecture and Definition-of-Done review.

## Sprint 13 closure

Sprint 13 is formally closed.

Delivered flow:

```text
Immutable Review Package
        ↓
Manifest
        ↓
Schema-managed SQLite History
        ↓
Explicit Import State
        ↓
Timeline Queries
        ↓
Compatibility
        ↓
Snapshot Comparison
        ↓
Exact / Normalized Replay
        ↓
Read-only CLI
```

Stable historical source-of-truth rule:

```text
Archived Review Package JSON = canonical historical evidence
manifest.jsonl               = append-only index
history.db                   = rebuildable projection
```

## Sprint 14 objective

Sprint 14 should add the first **outcome-aware** historical intelligence while preserving the evidence semantics established in Sprints 12–13.

The sprint must answer concrete historical questions such as:

- What happened after a historical recommendation?
- Over what explicitly defined observation window?
- Which price evidence was actually available for that observation?
- Did the recommendation remain stable, reverse, or disappear before the observation matured?
- How should incomplete outcome evidence be represented?
- Which conclusions are descriptive facts and which would be unsupported causality claims?

Sprint 14 must not turn snapshot value changes into implicit investment performance.

## Sprint 14 guardrails

Keep these rules stable:

- no hindsight leakage;
- no rewriting archived evidence;
- no silent use of present-day data as historical evidence;
- no performance claims without an explicit methodology;
- no unsupported causality claims;
- no false precision from small samples;
- no confidence calibration before sample-size requirements are defined;
- no Knowledge Domain before outcome semantics are stable;
- no external-data reconstruction without provenance and version contracts.

## Current architectural baseline

### Comparison

`HistoricalSnapshotComparisonService` is the aggregate read-only comparison boundary.

It consumes typed History repositories and compatibility assessment.

It does not own raw SQL and does not calculate portfolio performance.

### Replay

`HistoricalReplayService` supports:

```text
EXACT_ARCHIVED_PACKAGE
NORMALIZED_HISTORICAL_VIEW
```

`CURRENT_CODE_RECALCULATION` remains defined but unsupported.

Replay never accesses external data.

### CLI

CLI remains a composition/rendering boundary.

No History query, comparison, replay, or future outcome business rule belongs directly in CLI code.

## Quality baseline

After each logical package:

```powershell
python -m pytest tests\<focused-test>.py -q
python -m pytest -q
```

The passing-test count is intentionally not hard-coded as a permanent project metric.

## Near-term priorities

1. Define historical outcome questions and terminology.
2. Define explicit observation-window models.
3. Define outcome evidence provenance before adding calculations.
4. Add read models/repositories only where current History data can support them.
5. Separate recommendation transition facts from later price outcome facts.
6. Add outcome calculations only after missing-data and window semantics are explicit.
7. Add CLI only after the service boundary exists.
8. Add a realistic deterministic Sprint 14 fixture before closure.

## Deferred capabilities

Not currently implemented:

- current-code historical recalculation;
- external-context historical replay;
- portfolio performance attribution;
- tax-lot performance;
- multi-currency historical performance conversion;
- recommendation effectiveness scoring;
- confidence calibration from historical outcomes;
- factor-effectiveness inference;
- Knowledge Domain;
- autonomous trading.

## Stable decisions

Keep these unless requirements materially change:

- immutable historical packages;
- append-only manifest;
- SHA-256 verification;
- exclusive archive creation;
- verified bytes are the bytes later decoded and parsed;
- timezone-aware persisted timestamps;
- stable-key historical identity;
- deterministic ordering;
- Review Domain as assembly boundary;
- History Domain as evidence/persistence boundary;
- Historical Intelligence as relationship-analysis boundary;
- CLI as composition boundary;
- archived JSON as historical source of truth;
- SQLite as rebuildable History projection;
- History repositories own History persistence queries.
