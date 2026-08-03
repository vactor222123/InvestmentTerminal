# Investment Terminal

> A long-term investment analysis platform built around deterministic analysis, transparent decisions, and preserved historical evidence.

**Status:** Active development  
**Current architectural milestone:** Sprint 12 — Historical Intelligence Foundation  
**Primary language:** Python

---

## Overview

Investment Terminal is a modular investment analysis system for long-term investing, portfolio management, and disciplined review workflows.

The product combines:

- portfolio modelling;
- market and stock analysis;
- technical indicators;
- ranking and recommendation logic;
- capital deployment planning;
- structured Review Packages;
- immutable historical snapshots;
- SQLite-based historical analysis;
- timeline generation.

The project is designed as a long-lived product rather than a collection of scripts.

Its central principle is:

> Preserve verified evidence, keep calculations deterministic, and make every important conclusion traceable.

---

## Product Direction

Investment Terminal is evolving through three major layers:

```text
Current-State Analysis
        ↓
Historical Intelligence
        ↓
Future Knowledge and Confidence Systems
```

### Current-State Analysis

The system evaluates:

- portfolio structure;
- cost basis and market value;
- available capital;
- stock and ETF candidates;
- technical indicators;
- ranking signals;
- recommendations;
- deployment plans.

### Historical Intelligence

Completed reviews can become permanent historical evidence:

```text
Review Package
        ↓
Immutable Snapshot Archive
        ↓
Append-only Manifest
        ↓
Verified Import
        ↓
SQLite History
        ↓
Timeline Events
```

### Future Knowledge Layer

Planned capabilities include:

- historical comparison;
- confidence calibration;
- recommendation outcome tracking;
- evidence relationships;
- decision traceability;
- knowledge extraction from prior reviews.

---

## Core Principles

Investment Terminal prioritizes:

1. Correctness
2. Determinism
3. Historical integrity
4. Explainability
5. Maintainability
6. Extensibility
7. Performance

The system should never silently hide missing, stale, inconsistent, or unverified data.

---

## Main Capabilities

### Portfolio Domain

Portfolio capabilities include:

- current portfolio models;
- portfolio holdings;
- cost-basis snapshots;
- market-value enrichment;
- cash tracking;
- target allocation;
- sleeve and strategy breakdowns;
- contribution planning;
- policy-gap analysis;
- portfolio review adaptation.

Portfolio data is represented through explicit domain models rather than loosely shared dictionaries.

---

### Market Data

The market-data layer supports structured quote acquisition and persistence.

Current architecture includes:

- quote models;
- quote repositories;
- market-price loading;
- freshness metadata;
- portfolio quote integration;
- support for external market-data providers.

External data must be validated before it influences recommendations or historical evidence.

---

### Technical and Stock Analysis

The analytical layer supports indicators and ranking inputs such as:

- RSI;
- moving averages;
- EMA;
- MACD;
- MACD signal and histogram;
- ATR;
- average volume;
- 52-week high and low;
- stock-ranking data;
- portfolio recommendation exports;
- investment thesis data.

The project is designed so new stocks and ETFs can be added without rewriting the core architecture.

---

### Review Package

The Review Domain assembles a unified structured artifact from multiple analytical sources.

A Review Package may include:

- data freshness;
- market analysis;
- stock analysis;
- opportunities;
- machine recommendations;
- portfolio summary;
- holdings;
- allocation and deployment decisions;
- source-package evidence.

The Review Domain assembles information. It does not replace the analytical domains that produced it.

---

## Historical Intelligence

Sprint 12 introduced the first complete History Domain.

### Historical Snapshot

Each archived review receives canonical metadata:

- snapshot UUID;
- optional package ID;
- package schema version;
- product version;
- generation timestamp;
- archive timestamp;
- archive path;
- SHA-256 checksum;
- optional supersession relationship;
- status.

Historical timestamps are timezone-aware.

---

### Immutable Archive

Archived Review Packages are stored as exact JSON bytes.

Default structure:

```text
data/
└── history/
    ├── manifest.jsonl
    ├── history.db
    └── YYYY/
        └── MM/
            └── <generated-at>_<snapshot-id>.json
```

Archive rules:

- completed snapshots are never overwritten;
- archive paths are unique;
- exact bytes are preserved;
- corrections create new snapshots;
- checksum verification detects modification.

The archived JSON is the canonical historical Source of Truth.

---

### Append-only Manifest

The manifest is stored as JSON Lines:

```text
data/history/manifest.jsonl
```

It provides an append-only index for:

- snapshot identity;
- archive location;
- package identity;
- schema version;
- timestamps;
- checksums;
- supersession metadata.

The manifest does not replace the archived package.

---

### SQLite History

Structured historical data is stored in:

```text
data/history/history.db
```

Current tables:

```text
schema_metadata
snapshots
portfolio_summary
holdings
recommendations
deployment
timeline_events
```

SQLite is a rebuildable query and analytics representation.

It is not the canonical evidence store.

---

### Verified Historical Loading

Before archived evidence is imported, the loader verifies:

- archive-root path safety;
- file existence;
- exact SHA-256 checksum;
- UTF-8 encoding;
- valid JSON;
- object structure;
- package schema version;
- matching generation timestamp.

Unverified archives must not be used for historical analysis.

---

### Historical Import

The import pipeline normalizes:

```text
Archived Review Package
        ↓
portfolio_summary
holdings
recommendations
deployment
timeline_events
```

The pipeline:

- requires registered snapshot metadata;
- prevents repeat imports;
- preserves original recommendation and deployment payloads;
- removes misleading partial detail rows after failure;
- keeps valid snapshot metadata intact.

---

### Timeline Events

Current event types:

```text
SNAPSHOT_ARCHIVED
PORTFOLIO_SUMMARY_RECORDED
HOLDING_RECORDED
RECOMMENDATION_RECORDED
DEPLOYMENT_RECORDED
```

Timeline events provide the first foundation for future:

- portfolio evolution;
- recommendation history;
- deployment history;
- review replay;
- snapshot comparison.

---

## Command-Line Workflows

Run commands from the repository root with the virtual environment activated.

### Activate the virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

The virtual environment must normally be activated again after opening a new terminal.

---

### Generate a Review Package

```powershell
python -m investment_terminal.cli.investment_review_package
```

Available options can be inspected with:

```powershell
python -m investment_terminal.cli.investment_review_package --help
```

---

### Archive a Review Package

```powershell
python -m investment_terminal.cli.archive_review_package
```

Inspect supported arguments:

```powershell
python -m investment_terminal.cli.archive_review_package --help
```

---

### Import Historical Data

Default workflow:

```powershell
python -m investment_terminal.cli.import_history
```

This command:

1. synchronizes `manifest.jsonl` with SQLite;
2. verifies archived Review Packages;
3. imports structured historical data;
4. builds timeline events;
5. skips already imported records.

Metadata only:

```powershell
python -m investment_terminal.cli.import_history --metadata-only
```

One snapshot:

```powershell
python -m investment_terminal.cli.import_history `
    --snapshot-id <snapshot-uuid>
```

JSON report:

```powershell
python -m investment_terminal.cli.import_history --json
```

Custom paths:

```powershell
python -m investment_terminal.cli.import_history `
    --history-root data\history `
    --manifest data\history\manifest.jsonl `
    --database data\history\history.db
```

---

## Typical Historical Workflow

```text
1. Generate Review Package
2. Archive Review Package
3. Register snapshot in manifest
4. Synchronize manifest with SQLite
5. Verify archived JSON
6. Import normalized history
7. Build timeline events
```

Current commands:

```powershell
python -m investment_terminal.cli.investment_review_package
python -m investment_terminal.cli.archive_review_package
python -m investment_terminal.cli.import_history
```

Direct automatic archival from the Review Package CLI is intentionally not enabled yet. The workflows remain separate until a stable orchestration boundary is added.

---

## Project Structure

High-level structure:

```text
InvestmentTerminal/
├── config/
├── data/
├── docs/
├── investment_terminal/
│   ├── cli/
│   ├── history/
│   ├── market_data/
│   ├── portfolio/
│   ├── review/
│   └── ...
├── logs/
├── output/
├── tests/
├── README.md
└── requirements.txt
```

### Important History Modules

```text
investment_terminal/history/
├── historical_snapshot_models.py
├── historical_snapshot_archive.py
├── historical_snapshot_manifest.py
├── historical_snapshot_service.py
├── historical_sqlite_store.py
├── historical_snapshot_repository.py
├── historical_manifest_import_service.py
├── historical_review_package_loader.py
├── historical_portfolio_summary_importer.py
├── historical_holdings_importer.py
├── historical_recommendations_importer.py
├── historical_deployment_importer.py
├── historical_timeline_builder.py
└── historical_import_pipeline.py
```

### History CLI Modules

```text
investment_terminal/cli/
├── archive_review_package.py
├── import_history.py
└── investment_review_package.py
```

---

## Installation

### 1. Clone the repository

```powershell
git clone <repository-url>
cd InvestmentTerminal
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## Testing

Run the full test suite:

```powershell
python -m pytest
```

Run one test file:

```powershell
python -m pytest tests\test_historical_import_pipeline.py
```

Run History-related tests:

```powershell
python -m pytest tests\test_historical_snapshot_models.py
python -m pytest tests\test_historical_snapshot_archive.py
python -m pytest tests\test_historical_snapshot_manifest.py
python -m pytest tests\test_historical_sqlite_store.py
python -m pytest tests\test_historical_snapshot_repository.py
python -m pytest tests\test_historical_manifest_import_service.py
python -m pytest tests\test_historical_review_package_loader.py
python -m pytest tests\test_historical_portfolio_summary_importer.py
python -m pytest tests\test_historical_holdings_importer.py
python -m pytest tests\test_historical_recommendations_importer.py
python -m pytest tests\test_historical_deployment_importer.py
python -m pytest tests\test_historical_timeline_builder.py
python -m pytest tests\test_historical_import_pipeline.py
python -m pytest tests\test_import_history_cli.py
```

Every new module should be accompanied by focused tests and a green full regression suite.

---

## Development Workflow

Recommended workflow:

```powershell
git checkout develop
git pull origin develop
```

Create or update one focused component, then run:

```powershell
python -m pytest tests\<focused-test-file>.py
python -m pytest
```

Commit one logical change:

```powershell
git add <files>
git commit -m "<type>(<scope>): <description>"
git push origin develop
```

Preferred rule:

> One focused module, one focused test set, one logical commit.

---

## Line Endings

The repository primarily uses LF line endings.

Recommended `.gitattributes` policy:

```gitattributes
* text=auto eol=lf

*.bat text eol=crlf
*.cmd text eol=crlf
*.ps1 text eol=crlf

*.py text eol=lf
*.md text eol=lf
*.json text eol=lf
```

Git warnings about LF being replaced by CRLF are usually line-ending notices, not Python errors.

---

## Data and Evidence Model

The canonical hierarchy is:

```text
Immutable archived Review Package
        ↓
Append-only manifest metadata
        ↓
Rebuildable SQLite history
        ↓
Derived timeline
        ↓
Future knowledge
```

Rules:

- evidence is preserved before interpretation;
- structured databases may be rebuilt;
- original payloads should not be silently discarded;
- derived data must not invent absent facts;
- important timestamps must remain explicit;
- historical integrity takes priority over convenience.

---

## Documentation

Canonical documentation is stored in:

```text
docs/
```

Important files include:

```text
PROJECT_VISION.md
CONSTITUTION.md
ARCHITECTURE.md
DATA_MODEL.md
INVESTMENT_PHILOSOPHY.md
DESIGN_PRINCIPLES.md
DEVELOPMENT_GUIDELINES.md
QUALITY_ATTRIBUTES.md
PRODUCT_VALUES.md
GLOSSARY.md
DOMAIN_MAP.md
ROADMAP.md
SPRINT_11_REVIEW.md
SPRINT_12_PLAN.md
SPRINT_12_REVIEW.md
```

Architecture Decision Records are stored in:

```text
docs/adr/
```

Documentation is part of the engineering work and should evolve with the code.

---

## Current Limitations

The Historical Intelligence foundation is implemented, but the following capabilities remain future work:

- direct archive integration with Review Package generation;
- public timeline query service;
- historical replay CLI;
- snapshot-to-snapshot comparison;
- recommendation outcome tracking;
- schema migration framework;
- archive integrity audit command;
- manifest rebuild tools;
- Knowledge Domain;
- confidence calibration.

These are extensions of the current architecture rather than reasons to replace it.

---

## Roadmap Direction

### Near-term

- complete documentation alignment after Sprint 12;
- timeline query APIs;
- replay support;
- snapshot comparison;
- schema migration foundation;
- end-to-end tests using real Review Package output.

### Medium-term

- historical portfolio evolution;
- recommendation history;
- deployment outcome tracking;
- confidence history;
- evidence relationships.

### Long-term

- Knowledge Domain;
- historical pattern extraction;
- decision memory;
- confidence calibration;
- explainable AI synthesis grounded in archived evidence.

---

## Security and Privacy

Investment Terminal may process sensitive financial data.

Rules:

- never commit credentials;
- keep API keys outside version control;
- avoid personal data in fixtures;
- treat historical archives and SQLite databases as sensitive;
- do not expose local portfolio data without explicit user action;
- validate archive paths before reading files.

The project is local-first unless future synchronization features are explicitly introduced.

---

## License

Personal Use.

Copyright © Viktor and contributors.

---

## Disclaimer

Investment Terminal is intended to support investment research and portfolio review.

It does not provide financial advice.

All investment decisions remain the responsibility of the investor.

Market data, analysis, rankings, recommendations, and historical comparisons may be incomplete or incorrect and must be reviewed critically.

---

## Mission

Build a reliable private investment analysis platform that:

- uses transparent and validated data;
- keeps calculations deterministic;
- explains important decisions;
- preserves every completed review as evidence;
- learns from history without rewriting it;
- remains maintainable for many years.

> Investment Terminal should be able to explain not only what it believes now, but what it believed before and why.
