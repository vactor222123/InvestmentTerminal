# Investment Terminal — Design Principles

**Status:** Canonical Product Design Principles  
**Updated after:** Sprint 13 — Historical Comparison and Replay

## 1. Priority Order

1. Correctness
2. Determinism
3. Integrity
4. Explainability
5. Simplicity
6. Extensibility
7. Performance

Performance never outranks correctness or historical integrity.

## 2. Single Responsibility

Every module has one primary reason to change.

Examples:

- archive preserves bytes;
- manifest indexes snapshots;
- repositories own persistence queries;
- compatibility service decides comparability;
- leaf comparators calculate only one comparison type;
- aggregate comparison service orchestrates;
- replay service orchestrates supported replay modes;
- CLI formats and invokes.

## 3. Explicit Dependencies

Dependencies are injected and visible.

Application services may compose repositories and comparators. They must not hide global state or external data access.

## 4. Canonical Models

Stable business concepts require typed canonical models rather than anonymous dictionaries.

Boundary dictionaries remain appropriate for:

- JSON;
- archive payloads;
- serialization;
- CLI JSON output.

## 5. Persistence Query Ownership

History-domain repositories own History persistence queries.

Consequences:

- no raw SQL in CLI;
- no raw SQL in comparison services;
- no raw SQL in replay services;
- new read requirements receive explicit typed repository boundaries.

## 6. Exact Evidence vs Rebuildable Projection

Exact archived Review Package bytes are canonical historical evidence.

SQLite is a rebuildable query projection.

A normalized view must never be represented as exact archived evidence.

## 7. Read Once, Verify Once

Archive verification and deserialization must operate on the same verified byte buffer.

A verified path must not be reopened afterward for semantic parsing.

## 8. Atomic Historical Import

Detail import is one transaction owned by `HistoricalImportPipeline`.

```text
portfolio_summary
→ holdings
→ recommendations
→ deployment
→ timeline
```

A failed import rolls back the whole detail batch.

## 9. Explicit Workflow State

Import completeness is represented by `HistoricalImportState`, not inferred from row presence.

States are explicit and transitions are validated.

## 10. Stable Historical Identity

Historical collection comparison uses persisted stable keys.

Never infer equivalence through fuzzy symbol/name matching when keys differ.

Different keys mean different historical identities unless an explicit migration/identity policy says otherwise.

## 11. Compatibility Before Comparison

Cross-snapshot comparison first evaluates chronology, schema support, portfolio identity, currency, source status, and detail availability.

Hard incompatibility short-circuits leaf comparison.

Soft incompatibility remains visible as warnings.

## 12. No Performance Claims from Value Deltas

A portfolio value change is a mathematical delta, not automatically investment performance.

Historical comparison must not label value differences as return/performance without a dedicated performance methodology.

## 13. Replay Safety

Supported replay modes must be explicit.

Sprint 13 supports:

- exact archived package;
- normalized historical view.

Current-code recalculation is deferred and must not be silently executed.

Replay never accesses external data.

## 14. Thin CLI

CLI responsibilities:

```text
parse
→ configure
→ invoke
→ format
```

No domain calculations or persistence invariants belong in CLI modules.

## 15. Evidence Before Narrative

Facts, warnings, provenance, source status, and missing data remain explicit.

AI interpretation may explain evidence but does not rewrite canonical facts.
