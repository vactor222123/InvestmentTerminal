# Investment Terminal — Quality Attributes

**Status:** Canonical Quality Standard  
**Updated after:** Sprint 13 — Historical Comparison and Replay

## 1. Reliability

Required:

- validated inputs;
- explicit errors;
- deterministic workflows;
- atomic historical import;
- explicit import state;
- no silent partial success;
- actionable CLI failures.

## 2. Determinism

Identical historical evidence must produce identical normalized imports, timeline ordering, comparison results, and replay payloads.

Stable keys and deterministic ordering are mandatory.

## 3. Integrity

History integrity requires:

- exact-byte archive preservation;
- SHA-256 verification;
- archive-root confinement;
- symlink/path protections;
- package schema and timestamp identity validation;
- append-only manifest;
- schema migration control;
- transactional detail import.

## 4. Traceability

Historical conclusions must be traceable:

```text
Comparison / Replay
→ Typed historical projection
→ HistoricalSnapshot
→ Archived Review Package
```

Exact replay terminates directly at verified archived evidence.

## 5. Historical Immutability

Archived Review Packages are never overwritten.

Corrections create new snapshots with explicit lineage.

Manifest entries remain append-only.

SQLite may be rebuilt.

## 6. Rebuildability

Rebuildable components include:

- synchronized SQLite snapshot metadata;
- import state;
- portfolio summary;
- holdings;
- recommendations;
- deployment;
- timeline events.

The archive is not rebuildable from SQLite and therefore remains canonical.

## 7. Compatibility Safety

Comparison must not proceed silently across incompatible historical identities.

Compatibility states and warnings are explicit.

Source-status changes are surfaced.

## 8. Replay Safety

Exact and normalized replay are distinct.

Normalized replay must warn that SQLite is a rebuildable projection.

Unsupported current-code recalculation is rejected.

## 9. Maintainability

Responsibilities remain separated across:

- models;
- repositories;
- importers;
- comparators;
- application services;
- CLI.

History persistence queries remain behind repository boundaries.

## 10. Testability

Sprint 13 requires:

- focused unit tests;
- service integration tests;
- CLI tests;
- migration tests;
- atomicity tests;
- realistic deterministic end-to-end fixture;
- full regression suite.

## 11. Portability

Tests must avoid platform-specific filesystem assumptions such as renaming an open SQLite file.

Windows and POSIX behavior must be considered where file handles differ.

## 12. Observability

Errors should identify:

- missing database;
- missing snapshot;
- invalid archive;
- checksum mismatch;
- unsupported schema;
- invalid transition;
- comparison incompatibility;
- unsupported replay mode.

## 13. Security and Safety

Local historical integrity still requires defensive handling of:

- unsafe paths;
- symlinks;
- malformed JSON;
- malformed UUID/checksum values;
- unsupported future schema versions.

## 14. Definition of Trustworthy History

A trustworthy historical result is:

- rooted in immutable evidence;
- validated;
- explicitly versioned;
- queryable through typed boundaries;
- comparable only under explicit compatibility policy;
- replayed without hidden recalculation.
