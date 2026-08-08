# Investment Terminal

> Professional private investment intelligence system

## Overview

Investment Terminal is a modular Python application for deterministic investment analysis, portfolio intelligence, structured review generation, immutable history, historical comparison, and safe replay.

The system is designed around five non-negotiable properties:

- correctness;
- determinism;
- traceability;
- historical integrity;
- explicit human decision ownership.

The Python engine produces structured evidence. AI may interpret that evidence together with current external context, but AI does not replace canonical calculations, archived facts, or the final human decision.

## Current Product Capabilities

### Current-state intelligence

- market-data acquisition and validation;
- technical and fundamental analysis;
- ranking and machine recommendations;
- portfolio holdings and policy;
- cost-basis and market-value portfolio views;
- contribution and deployment planning;
- versioned Review Package generation.

### History

Investment Terminal preserves completed Review Packages as immutable historical evidence.

Current History capabilities include:

- canonical `HistoricalSnapshot`;
- immutable exact-byte JSON archive;
- SHA-256 integrity verification;
- append-only `manifest.jsonl`;
- SQLite historical projection;
- controlled schema migrations;
- explicit snapshot import state;
- atomic detail import;
- typed timeline events and timeline queries;
- snapshot navigation;
- portfolio-summary, holdings, recommendation, and deployment repositories.

### Historical comparison

Implemented comparison capabilities include:

- snapshot compatibility assessment;
- portfolio-summary comparison;
- holdings comparison by stable key;
- recommendation comparison by stable key;
- deployment comparison by stable key;
- aggregate `SnapshotComparison`.

Comparison explicitly distinguishes:

- `COMPATIBLE`;
- `PARTIALLY_COMPATIBLE`;
- `INCOMPATIBLE`.

Source-status changes and missing historical detail remain visible rather than being silently ignored.

### Historical replay

Supported replay modes:

- `EXACT_ARCHIVED_PACKAGE`;
- `NORMALIZED_HISTORICAL_VIEW`.

`CURRENT_CODE_RECALCULATION` is defined in the domain contract but intentionally unsupported.

Exact replay uses verified archived evidence. Normalized replay uses the rebuildable typed SQLite projection.

## History CLI

```powershell
python -m investment_terminal.cli.import_history
python -m investment_terminal.cli.query_history snapshots
python -m investment_terminal.cli.query_history timeline
python -m investment_terminal.cli.query_history show --snapshot-id <uuid>

python -m investment_terminal.cli.compare_history `
    --earlier <snapshot-uuid> `
    --later <snapshot-uuid>

python -m investment_terminal.cli.replay_history `
    --snapshot-id <uuid> `
    --mode exact

python -m investment_terminal.cli.replay_history `
    --snapshot-id <uuid> `
    --mode normalized `
    --json
```

All History query/comparison/replay CLIs are read-only inspection boundaries. They do not contain SQL or domain calculations.

## Historical Source-of-Truth Rule

```text
Archived Review Package JSON
    canonical historical evidence

manifest.jsonl
    append-only navigation index

history.db
    rebuildable structured projection
```

SQLite may be rebuilt. Archived Review Package bytes must not be rewritten.

## Architecture

Investment Terminal is a modular monolith with domain-oriented boundaries.

Primary domains:

- Market Data;
- Technical Analysis;
- Fundamental Analysis;
- Ranking;
- Recommendation;
- Portfolio;
- Decision;
- Review;
- History;
- Historical Intelligence;
- future Knowledge.

CLI modules construct dependencies and invoke application services. Repositories own History persistence queries. Comparators and replay logic operate through typed domain boundaries.

## Testing

Sprint 13 includes a realistic end-to-end History fixture covering:

```text
Review Package
→ Archive
→ Manifest
→ SQLite synchronization
→ Verified atomic import
→ Timeline
→ Query
→ Comparison
→ Replay
```

The fixture is deterministic and network-free.

## Project Philosophy

**Data Quality First. Evidence Before Narrative. History Is Immutable.**

The application must never fabricate unavailable data, hide uncertainty, or silently reinterpret historical evidence.

## Disclaimer

Investment Terminal is research and decision-support software. It does not provide financial advice and does not execute trades. The investor remains responsible for every investment decision.
