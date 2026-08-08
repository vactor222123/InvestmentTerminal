# Investment Terminal — Glossary

**Status:** Canonical Terminology  
**Updated after:** Sprint 13 — Historical Comparison and Replay

## Archived Review Package

The exact immutable JSON bytes of a completed Review Package preserved by History. This is canonical historical evidence.

## Canonical Evidence

Evidence whose original meaning and bytes are authoritative for historical verification. For History, the archived Review Package is canonical evidence.

## Canonical Model

The primary typed data model representing one business concept.

## Compatibility

The explicit assessment of whether two historical snapshots can be meaningfully compared.

Statuses:

- `COMPATIBLE`;
- `PARTIALLY_COMPATIBLE`;
- `INCOMPATIBLE`.

## Comparison Facts

A minimal typed read model containing only facts required to evaluate snapshot compatibility.

## Deployment

A proposed allocation of available capital into portfolio sleeves or assets.

## Evidence

Validated information used to support deterministic calculations, recommendations, historical comparisons, or replay.

## Exact Replay

Replay mode that returns the verified archived Review Package payload.

Canonical mode name:

`EXACT_ARCHIVED_PACKAGE`.

## Historical Intelligence

The domain capability that analyzes relationships across verified historical facts.

Sprint 13 implements compatibility, snapshot comparison, and safe replay foundations.

## Historical Replay

A controlled representation of one historical snapshot.

Supported Sprint 13 forms are exact archived evidence and normalized historical view.

## Historical Snapshot

Canonical immutable metadata describing one archived Review Package.

## History

The domain responsible for preserving, verifying, indexing, importing, and querying historical evidence.

History owns facts. Historical Intelligence owns relationships between facts.

## Import State

The explicit persisted workflow state of a historical snapshot import.

Values:

- `METADATA_ONLY`;
- `VERIFIED`;
- `IMPORTING`;
- `IMPORTED`;
- `FAILED`.

## Knowledge

Future reusable, traceable patterns or conclusions derived from accumulated historical evidence and Historical Intelligence outputs.

Knowledge never rewrites History.

## Manifest

Append-only JSON Lines index of `HistoricalSnapshot` metadata.

The manifest is navigation metadata, not canonical evidence.

## Normalized Historical View

Replay representation constructed from typed SQLite History repositories.

Canonical mode name:

`NORMALIZED_HISTORICAL_VIEW`.

It is rebuildable and is not exact archived evidence.

## Recommendation

A deterministic machine-generated assessment derived from analysis. It is not investment advice.

## Replay Provenance

Metadata identifying the historical evidence behind replay, including snapshot ID, package schema version, and archive SHA-256.

## Review Package

The canonical versioned structured output assembled by the Review Domain for one analysis run.

## Schema Migration

Controlled transformation of the History SQLite schema from one supported version to the next.

## Snapshot Comparison

Typed aggregate result describing changes between two compatible historical snapshots.

## Source Status

The provenance state of portfolio values, such as `COST_BASIS_ONLY` or `MARKET_VALUE_CONNECTED`.

A source-status change is significant historical context and must remain visible.

## Source of Truth

The canonical location for one category of information.

For historical evidence:

- archived JSON = canonical evidence;
- manifest = append-only index;
- SQLite = rebuildable projection.

## Stable Key

Persisted identity used to match historical collection items across snapshots.

Examples:

- `holding_key`;
- `recommendation_key`;
- `deployment_key`.

Comparators do not fuzzy-match different stable keys.

## Timeline Event

Typed historical event derived from one normalized snapshot import.

## Current-Code Recalculation

A defined but unsupported replay mode in Sprint 13.

Canonical mode name:

`CURRENT_CODE_RECALCULATION`.

It must not be silently executed.
