# Canonical Live Analysis Contract

Sprint 33 Task 1 formalizes the current-state equity-analysis authority without
creating a second analysis engine or schema.

## Existing Pipeline

The established live pipeline remains:

```text
configured universe
→ Yahoo historical OHLCV refresh
→ trading-session freshness enforcement
→ technical analysis
→ Yahoo fundamental snapshot
→ sector-aware fundamental scoring
→ asset decisions
→ ranking
→ coverage-aware recommendations
→ investment theses
→ target allocation
→ PortfolioExportPackage
```

The current CLI `investment_terminal.cli.portfolio_ranking` remains the
composition owner during Task 33.1.

## Canonical Typed Result

The canonical result is the existing:

```text
PortfolioExportPackage
```

named by the analysis contract as:

```text
CurrentStateEquityAnalysisResult
```

Contract identity:

```text
CURRENT_STATE_EQUITY_ANALYSIS@1
```

This is intentionally a type alias, not a wrapper dataclass.

Why:

```text
PortfolioExportPackage already owns
- schema_version
- generated_at
- universe_name
- market_data freshness result
- ranking
- recommendations
- theses
- allocation
```

`PortfolioExporter.build_package()` already validates cross-component symbol,
rank, universe-size, currency, readiness, and timestamp consistency.

Duplicating those fields into another "analysis result" model would create two
authorities for the same deterministic state.

## Serialization

Task 33.1 does not change the existing JSON export schema.

```text
PortfolioExporter.SCHEMA_VERSION == 1.3
```

remains authoritative for the serialized stock-analysis artifact.

The analysis contract identity and serialized schema version serve different
purposes:

```text
CURRENT_STATE_EQUITY_ANALYSIS@1
    semantic typed analysis boundary

Portfolio export schema 1.3
    serialized compatibility contract
```

## Review Package Boundary

The existing JSON path remains:

```text
PortfolioExportPackage
→ to_dict()
→ JSON file
→ PortfolioAnalysisPackageLoader
→ PortfolioAnalysisReviewAdapter
→ Review Package
```

Task 33.1 does not remove that compatibility path.

Task 33.2 will add direct typed composition:

```text
CurrentStateEquityAnalysisResult
→ Review Package
```

without requiring the intermediate JSON round-trip.

## Authority Rule

Current-state analysis remains upstream of Review Package:

```text
external/current data
→ deterministic current-state analysis
→ Review Package
→ History
→ explicit History-to-Knowledge ingestion
→ Knowledge
→ grounded AI
```

The current-state analysis contract must not import or construct Knowledge,
History, grounded AI, or Review Package objects.

## Failure Semantics

A canonical current-state result requires market data that passed the existing
freshness policy.

The helper:

```text
require_current_state_equity_analysis_result(...)
```

fails closed for:

```text
untyped dictionaries / arbitrary payloads
non-PortfolioExportPackage values
non-ready market data
```

This prevents downstream direct composition from accidentally accepting an
unvalidated ad-hoc dictionary as live analysis.

## Non-Goals

Task 33.1 does not:

- move orchestration out of the current CLI;
- alter ranking/scoring algorithms;
- change provider integrations;
- change JSON schema 1.3;
- integrate Review Package directly;
- integrate History;
- add ETF/watchlist/news/macro analysis.

Those belong to later focused tasks.
