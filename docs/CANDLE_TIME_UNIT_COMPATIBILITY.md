# Candle timestamp and unit compatibility audit

Follow-up: A02 repository/provider implementation is recorded in
`CANDLE_UTC_SAFETY.md`. Six probes below are now ordinary regression tests;
the two A03 xfails remain open. This document preserves the audit baseline.

Classification: AUDIT. Fresh clean `develop` baseline:
`67362b6e1cd790858403a28d794f8a4955899835`.
No production code, SQLite schema, JSON contract, private file or provider changed.
This is the requested compatibility gate after A01/A04/A05, NOT an A02/A03 fix.

## Reproduced boundaries

| Boundary | Actual behavior | Consequence |
| --- | --- | --- |
| CandleRepository writes | Raw `timestamp.isoformat()` is the unique TEXT key | Equivalent instants produce separate rows; a different offset bypasses payload conflict detection |
| Repository validation | Checks datetime type, not timezone awareness | Naive values enter storage |
| Range/latest/earliest | SQL text comparison and ordering | Offset bounds can miss a UTC row; mixed offsets can select the wrong latest row |
| YahooFinanceClient timestamp projection | Assigns UTC to a naive source index | Missing source timezone is silently assumed, not evidenced |
| YahooChartMetadataClient | Uppercases metadata currency | `GBp` and `GBP` become indistinguishable before candles exist |
| Yahoo projection, MarketBatchRequest, repository | Uppercase supplied currency without scaling OHLC | A downstream-only guard cannot recover the lost source spelling |
| MarketBatchRequest checksum | Includes offset-preserving ISO request dates | UTC-normalizing request serialization would invalidate existing request/checkpoint bindings |

These are synthetic reproductions and source inspection, not claims that the
private database has any affected rows. The audit does not establish provider
unit conventions for every exchange or certify any GBP series. In particular,
capitalization is not sufficient evidence for converting an existing price.

The repository's three save_many consumers are historical import, projected
historical import and weekly refresh. Weekly refresh derives its overlap from
get_latest, reads get_range, compares timestamp/identity/currency and OHLCV before
saving. Thus a write-only timestamp fix leaves read-selection risk. Historical
imports propagate repository errors. Existing A01 atomic conflict behavior must
remain intact across equivalent-instant keys as well as exact strings.

SymbolCurrencyQualificationService persists the adapter's returned currency;
resumed successful outcomes are reused. Fixing only fresh metadata calls does
not requalify old successful currency checkpoints or their derived manifests.
No checkpoint should silently become authoritative unit evidence after an update.

## Compatibility decision

1. Keep existing evidence bytes, manifests, request checksums and JSON schemas
   unchanged. Do not normalize archived request dates in place.
2. Implement A02 at the candle storage/query boundary in the next package:
   aware inputs, canonical UTC keys and equivalent UTC query bounds; reject
   naive provider timestamps with the existing timestamp failure category.
   Preserve the instant, not the wall clock or a guessed exchange session date.
3. Before enabling canonical writes against legacy storage, explicitly detect
   noncanonical, naive, malformed and equivalent-instant duplicate rows. An
   existing offset row plus a new UTC row must not become two records. Fail closed
   on incompatible storage until a separately authorized migration is available.
   Do not add a full-history scan for every candle; establish and test the
   bounded validation/transaction strategy before claiming scalability.
4. Any future migration needs a verified backup, exclusive writer ownership,
   dry-run counts, rollback, and post-migration uniqueness/integrity checks.
   Equivalent-instant unequal OHLCV/currency is a conflict, never last-row-wins.
   Naive timestamps cannot be assigned a timezone without source evidence.
   Canonical UTC formatting must handle fractional seconds consistently for
   lexicographic range/order semantics; test subsecond boundaries explicitly.
5. A03 requires a source-unit-aware boundary upstream of uppercase conversion.
   Until a versioned unit contract is implemented, reject ambiguous source unit
   labels before they are lost. Do not silently divide OHLC, alter volume, or
   reinterpret existing GBP rows. Retain raw source label, evidenced target unit
   and conversion provenance in a deliberate future contract. Requalification
   must account for already successful metadata checkpoints and manifests.

There is no automatic migration or operational command in this package. The
next developer package is A02 implementation with a legacy-storage gate and
tests; A03 implementation follows with explicit source-unit/checkpoint handling.
Neither depends on manually entering portfolio prices. A07 price-basis/source
provenance remains a separate open finding. Do not resume collection as a way
to work around these defects.

## Executable evidence

`tests/test_candle_time_unit_audit.py` contains eight **strict expected failures**
for the open defects and five passing controls. The xfails are NOT passing
acceptance tests and NOT proof of repair. Unexpected passes fail the suite;
when implementing the corresponding contract, remove the marker and retain or
strengthen the expectation. Include fail-closed legacy-storage fixtures rather
than bypassing the migration gate to satisfy a probe.

Controls cover canonical USD/EUR/GBP replay, existing batch conflict rollback,
and the fact that equivalent request windows currently have different checksums.
All SQLite files are synthetic pytest-local files and metadata is injected.
No network invocation, private integrity check or production data count is made.

Verification: focused 74 passed, 8 xfailed (3.84 s), including repository safety,
architecture and dependency guards. Full 3769 passed, 4 skipped, 8 xfailed
(48.82 s), one existing Starlette warning. `--runxfail` deliberately returned
exit 1: eight intended contract failures, five passing controls; failure causes
were inspected, not merely counted. `git diff --check` clean.
