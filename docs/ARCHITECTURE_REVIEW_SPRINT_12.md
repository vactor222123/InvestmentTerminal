# Architecture Review — Sprint 12

## Purpose

This document records the architecture review completed after Sprint 12 and defines the safest order of improvements before Sprint 13.

The review covered:

- portfolio models, loaders, pricing, allocation and audit flows;
- market-data services, clients, repositories and freshness logic;
- technical and fundamental analysis;
- decision, ranking and recommendation flows;
- review-package generation and export;
- history, immutable archives, manifests and structured SQLite imports;
- CLI orchestration, configuration and filesystem ownership;
- cross-domain dependencies, validation, timestamps, schema versions and tests.

## Executive verdict

The project has a usable and increasingly clear layered structure. The central analytical flow is understandable:

```text
market / fundamental data
        ↓
technical + fundamental analysis
        ↓
decision
        ↓
ranking
        ↓
recommendation
        ↓
review package
        ↓
history archive + SQLite analytical store
```

The architecture is suitable for continued development. A large rewrite is not recommended. The next step should be a small, controlled stabilization pass focused on ownership boundaries, persistence safety and shared conventions.

## BEFORE SPRINT 13

### 1. Centralize shared normalization rules

Create a small shared validation module for stable cross-domain primitives only:

```text
normalize_required_text
normalize_symbol
normalize_currency
validate_aware_datetime
validate_finite_number
validate_score_0_100
```

Do not move domain-specific business validation into this shared module.

### 2. Enforce timezone-aware datetimes consistently

Adopt one rule:

```text
All persisted and exported timestamps must be timezone-aware ISO-8601 values.
UTC is the canonical storage timezone.
```

Apply it consistently to quotes, candles, decisions, review packages and history records.

### 3. Make filesystem writes atomic where replacement is allowed

For mutable JSON outputs:

```text
write temporary file
flush and close
replace destination atomically
```

Immutable archive creation should remain append-only and use exclusive creation.

### 4. Clarify transaction ownership

Use this rule:

```text
Simple repositories may own single-operation transactions.
Multi-table history imports must own one transaction at service/importer level.
```

Rollback behavior must be covered by tests.

### 5. Define archive/manifest partial-failure recovery

Explicitly handle:

```text
archive file created
manifest append fails
```

Raise a clear integrity error and provide deterministic reconciliation or compensation behavior.

### 6. Make schema-version ownership explicit

```text
Decision schema version        → Decision Domain
Recommendation schema version  → Recommendation Domain
Review package schema version   → Review Domain
History SQLite schema version   → History Domain
```

Do not reuse one global schema version for unrelated serialized contracts.

### 7. Add architecture-level dependency tests

Verify that:

- domain models do not import CLI modules;
- history does not become a dependency of analytical domains;
- infrastructure does not import presentation/CLI code;
- review may depend on completed analytical outputs, but analytical domains do not depend on review packaging.

### 8. Expand failure-path tests

Prioritize:

- interrupted mutable file writes;
- malformed UTF-8 and JSON;
- timezone-naive timestamps;
- database rollback during multi-table import;
- duplicate archive paths and snapshot IDs;
- manifest failure after archive creation;
- checksum mismatch;
- generated-at mismatch;
- unsupported schema versions;
- missing required review sections.

## IMPROVE LATER

### 1. Replace free-form classifications gradually

Introduce enums or constrained value objects only where vocabularies are stable. Avoid a project-wide migration in one change.

### 2. Reduce repeated serialization code

Common helpers may later reduce repeated tuple-to-list and datetime-to-ISO conversion, but they must preserve each domain's public JSON contract.

### 3. Introduce repository protocols

Services should depend on narrow persistence protocols rather than concrete SQLite repositories where practical.

### 4. Improve configuration injection

Prefer explicit path/configuration injection. Keep `Settings` at the application composition boundary.

### 5. Consolidate output-path conventions

- configuration owns defaults;
- CLIs may override them;
- services receive resolved paths;
- domain models never calculate application filesystem locations.

### 6. Add database migrations

When the next history schema change is required, add explicit forward migrations rather than only changing the initial schema script.

### 7. Improve batch repository APIs

Accept general sequences or iterables where appropriate while preserving deterministic validation and transaction behavior.

### 8. Review duplicated risk and quality representations

Define one authoritative source for risk level and make derived representations explicit.

### 9. Add structured error types

```text
DomainValidationError
SerializationError
PersistenceError
ArchiveIntegrityError
ExternalProviderError
```

Introduce them incrementally, beginning with archive/history and provider boundaries.

## KEEP AS IS

- immutable historical review packages as the source of truth;
- append-only JSON Lines manifest;
- SHA-256 checksum metadata;
- exclusive archive file creation;
- deterministic ranking and recommendation behavior;
- frozen, slotted analytical models;
- explicit required review-package sections;
- separation of external clients from analytical models;
- CLI modules as composition and user-facing error boundaries.

## Domain summary

### Portfolio

Keep current state, valuation, policy gaps, contribution planning, allocation, ranking, recommendations and theses separated. Continue reducing coupling between portfolio state and analytical decisions.

### Market data

Provider, freshness, historical import and repository boundaries are generally sound. External API concerns should remain outside models and calculations.

### Technical analysis

Indicator calculations and scoring are suitably separated. Preserve deterministic numerical behavior and edge-case coverage.

### Fundamental analysis

Missing-data semantics and business-model applicability are strengths. Continue distinguishing unavailable data from genuinely weak fundamentals.

### Decision, ranking and recommendation

The pipeline is understandable and deterministic. Future improvements should focus on typed vocabularies and ownership of duplicated classifications.

### Review

The review package is an integration contract. It should assemble already calculated outputs rather than recalculate them.

### History

The History Domain has a strong direction: immutable evidence, append-only metadata and normalized query storage. Transactional import and recovery behavior deserve the highest persistence priority.

## Recommended implementation order

```text
1. Shared primitive validation and timezone rule
2. Atomic mutable JSON writes
3. History transaction and recovery behavior
4. Architecture dependency tests
5. Failure-path test expansion
6. Schema-version ownership documentation
7. Begin Sprint 13
8. Implement IMPROVE LATER items incrementally
```

## Sprint 13 entry criteria

Sprint 13 may begin when:

- all existing tests pass;
- timezone rules are consistent for persisted/exported timestamps;
- mutable JSON writes are atomic;
- history multi-table imports have tested rollback behavior;
- archive/manifest partial-failure behavior is documented and tested;
- dependency-direction tests are active;
- no unresolved critical architecture issue remains.

## Final conclusion

The codebase does not require a broad rewrite. The correct approach is controlled stabilization followed by continued feature development.

The highest-value work is making the existing boundaries reliable:

```text
clear ownership
consistent timestamps
safe persistence
predictable transactions
deterministic contracts
failure-path tests
```

After the BEFORE SPRINT 13 items are complete, the architecture is ready to support the next development phase.
