# Phase 4 — Context and Market Intelligence Closure

## Verified baseline

`develop @ f630bcabd032460657fb8329e82b9cae194b5bd7`

## Roadmap scope

| Scope | Evidence |
|---|---|
| News ingestion | `external_context_models.py`, `external_context_ingestion.py` |
| Macroeconomic data | `ExternalContextRecord` type `MACROECONOMIC` |
| Geopolitical context | `ExternalContextRecord` type `GEOPOLITICAL` |
| Events | `ExternalContextRecord` type `EVENT` with optional `event_at` |
| Sentiment/context evidence | `external_context_sentiment.py`, `external_context_review_adapter.py` |
| Provenance | `ExternalContextProvenance` and immutable provider identity |
| Freshness | `ExternalContextQualityService` with caller-configured maximum age |
| Explicit uncertainty | uncertainty level/reasons preserved in every normalized record |

The same provider-neutral ingestion boundary accepts NEWS, MACROECONOMIC,
GEOPOLITICAL, and EVENT records. Evidence can be stored through append-only
in-memory or versioned SQLite repositories and projected into the Review
Package without losing source, freshness, quality, or uncertainty.

## Architecture conclusion

Phase 4 follows the established direction: Context is an upstream evidence
domain, Review is the downstream assembly boundary, and neither external
providers nor sentiment methods gain recommendation authority. Provider output
is normalized and validated before persistence. Duplicate canonical or provider
identities fail closed. Missing provenance, stale evidence, uncertainty, and
missing sentiment assessments remain visible rather than being inferred away.

History, Knowledge, grounded AI, and automatic trade execution remain outside
the Phase 4 authority boundary.

## Verification

Package 6 was integrated at the verified baseline above. GitHub exposes no
separate workflow run or commit status for that SHA. The complete local suite
for the integrated package content passed with 2587 tests passed and 4 skipped.

Every Phase 4 roadmap item is represented by an implemented contract, service,
persistence boundary, Review projection, and focused tests. Phase 4 is closed.
The next roadmap phase is Phase 5 — Market Discovery.
