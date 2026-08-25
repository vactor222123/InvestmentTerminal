# Phase 7 Package 37 - Transaction Instrument-Metadata Enrichment Audit

Package type: `AUDIT`.

Source baseline: `develop @ 8dbf5e336d98b9e8c656c8be122f93af5ab0353e`.

## Scope

This package audits the repository boundary needed after the controlled private
offline quote qualification stopped on transaction-derived identities without
exchange tickers. It reads repository code, contracts, and synthetic tests only.
It does not read private transaction or quote inputs, mutate the transaction
database, create a valuation snapshot, or infer an exchange venue.

## Existing boundaries

- Transaction CSV import stores the complete `InstrumentIdentity` supplied by
  the source row, including optional exchange ticker and exchange code.
- The SQLite transaction repository preserves that identity inside each
  immutable transaction payload and reconstructs it losslessly.
- `PositionReconstructor` requires one identical instrument value for a stable
  instrument key across the complete ledger. Changing stored identities would
  therefore rewrite historical evidence and violate append-only ownership.
- `InstrumentIdentity.instrument_key` already prefers ISIN, then an
  exchange-scoped ticker, then ticker or symbol. The ten measured positions can
  therefore retain their stable keys while receiving separately verified venue
  metadata.
- `MarketMetadataProvenance` and `MarketMetadataQualityService` already provide
  timestamped source lineage, optional source-record checksum, and explicit
  `READY`, `PARTIAL`, or `STALE` quality.
- Current-portfolio holdings may contain exchange tickers, but that mutable
  private input has no per-instrument provenance and is not authoritative for
  enriching immutable transaction history.
- Maintained-universe evidence preserves provenance, but no populated matching
  universe or resolver for the private transaction instruments has been
  operationally demonstrated.
- Quote qualification and valuation currently read the reconstructed identity
  directly. Neither accepts a separate metadata projection or resolver.

## Measured gap

There is no provider-neutral, provenance-preserving instrument-metadata evidence
contract, JSON loader, or read-only service that can project an exchange ticker
onto an open position without changing its ledger transaction. Reusing the
private quote file as metadata authority would be circular: it proves only what
the caller typed into the quote input. Reusing `current_portfolio.json` would
also lose lineage. Guessing a ticker from a symbol, ISIN, broker document, or
venue is not an acceptable fallback.

## Smallest safe implementation package

Add one bounded read-only enrichment boundary with synthetic tests:

1. define immutable schema-version-1 per-instrument metadata evidence keyed by
   the existing canonical instrument key, carrying explicit `exchange_ticker`,
   optional `exchange_code`, and existing `MarketMetadataProvenance` plus quality;
2. load an explicit private JSON document with unique keys, strict fields,
   timezone-aware provenance, checksum validation, and deterministic ordering;
3. require exact open-position coverage and `READY` evidence; reject missing,
   extra, duplicate, stale, partial, future, key-changing, or conflicting
   metadata;
4. return a detached enriched position projection while preserving quantities,
   cost basis, currencies, ledger ownership, and source evidence; never update
   transaction rows or payloads;
5. add an optional explicit metadata input to offline quote qualification only,
   preserving the current schema-version-1 report and behavior when omitted;
6. keep valuation execution, online lookup, provider selection, maintained-
   universe ingestion, and transaction migration out of scope.

The first implementation must qualify metadata and quotes read-only. Wiring the
same verified projection into durable valuation requires a later package after
successful private qualification evidence.

## Next step

Implement the bounded instrument-metadata evidence, loader, projection service,
and optional offline-qualification composition described above using synthetic
and failure-path tests only. Do not request private metadata or execute valuation
until that implementation package is reviewed and pushed.

## Verification

```text
focused identity/metadata/transaction/reconstruction/qualification/privacy/architecture: 87 passed
full: 2780 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```
