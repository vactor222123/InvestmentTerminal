# Phase 7 Package 39 - Automated Instrument-Metadata Bootstrap Audit

Package type: `AUDIT`.

Source baseline: `develop @ 022075c15c77c81b755b545ecee0c3f34a71cc6c`.

## Trigger

The planned controlled metadata-backed qualification was stopped before any
runtime command or mutation. Requiring the operator to hand-author complete
provenance for every position is not an acceptable steady-state workflow. This
package audits the smallest safe automated bootstrap while preserving immutable
transactions and the Package 38 evidence contract.

## Existing evidence and limits

- The transaction ledger supplies stable ISIN-based keys for the measured open
  positions but lacks exchange tickers.
- The private quote input supplies candidate tickers, but cannot attest to its
  own correctness.
- The current-portfolio file may contain tickers but has no independent source
  record or per-instrument provenance.
- Package 38 can persist a reusable private metadata document and validate its
  freshness, lineage, exact coverage, and conflicts. Once generated from an
  independent source, that file already acts as the local reusable registry;
  a second persistence model is not yet justified.
- `READY` currently means complete and fresh provenance. It does not itself
  establish that a caller-authored source is authoritative.

## Verified provider capability

The official OpenFIGI API version 3 documentation defines `POST /v3/mapping`,
supports `ID_ISIN`, returns ticker and exchange-code candidates, preserves
request order, and permits unauthenticated use at lower limits. Without an API
key, one request accepts at most five mapping jobs and the mapping endpoint is
limited to 25 requests per minute. An API key raises the job limit to 100 but is
not required for the measured ten-position bootstrap.

Official documentation:

```text
https://www.openfigi.com/api/documentation
```

An ISIN may map to multiple exchange-level records. Therefore OpenFIGI output
cannot be reduced to one venue by taking the first row. Its `exchCode` is also
provider symbology and must not be silently presented as an ISO MIC or copied to
the internal optional `exchange_code` field.

## Smallest safe implementation

Add one bounded provider-backed bootstrap command that:

1. reconstructs open positions read-only and requires an ISIN key for every
   position requiring enrichment;
2. sends deterministic `ID_ISIN` mapping jobs to OpenFIGI v3 in batches of at
   most five without an API key, with an optional explicit API key;
3. archives exact response bytes privately and records their SHA-256;
4. accepts a ticker only when the independent response contains the exact
   candidate ticker already supplied by the private quote document; zero or
   conflicting matches fail closed, while repeated rows with the same ticker
   remain visible in private evidence;
5. leaves `exchange_code` null because OpenFIGI `exchCode` is not the internal
   MIC contract;
6. atomically writes the existing schema-version-1 metadata document with
   `OPENFIGI_V3` source, stable FIGI/source-record identity, observed/fetched
   time, and the exact archived-response checksum;
7. writes a separate redacted aggregate bootstrap report and never exposes
   ISINs, tickers, FIGIs, response bodies, paths, or credentials;
8. does not change transactions, run quote qualification, create valuation, or
   introduce a second registry database.

Synthetic tests must cover batching, request ordering, exact ticker
confirmation, no result, provider warning/error, ambiguous conflicting ticker,
duplicate same-ticker rows, malformed response, timeout/HTTP failure, optional
API-key handling, exact-byte archive/checksum, atomic metadata/report writes,
post-archive failure visibility, privacy, and architecture dependencies.

## Operator experience

After implementation, the ten existing mappings can be bootstrapped
automatically. The generated private metadata file is reused on later runs.
Operator input is needed only for a new ISIN, stale evidence, or an ambiguous or
conflicting provider result; routine quote qualification requires no repeated
manual metadata entry.

## Next step

Implement the bounded OpenFIGI v3 metadata-bootstrap command and redacted report
with synthetic tests only. Do not call OpenFIGI with private ISINs or run quote
qualification until that package is reviewed and pushed.

## Verification

```text
focused metadata/qualification/identity/reconstruction/privacy/architecture: 73 passed
full: 2793 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```
