# Phase 7 Package 34 - Offline Quote Qualification Audit

Package type: `AUDIT`.

Source baseline: `develop @ 55a7a310c091e5b6007f2aaf0ffa7ea89a5c4fd0`.

## Result

The JSON quote loader validates structure, unique canonical instrument keys,
positive finite prices, timezone-aware timestamps, and explicit currency/source.
The valuation service reconstructs open positions and then validates complete
quote lookup, canonical identity, exchange ticker, matching cost currency, and
`quoted_at <= valued_at` before appending a snapshot.

There is no read-only qualification boundary. The only current composition CLI
can append a private valuation snapshot, so it is not safe for first inspection
of private quote coverage. The quote JSON and transaction database contain
private evidence and must not be returned or committed.

## Smallest safe implementation

Add a parse/reconstruct-only qualification service and CLI with an atomic
schema-version-1 redacted report. It must load the transaction ledger and quote
JSON, reject transactions after an explicit `valued_at`, reconstruct positions,
validate complete one-to-one quote coverage plus identity/ticker/currency/time,
and report only status, timing, transaction/open-position/required/matched quote
counts, currency count, normalized failure, and limitations. It must not create
or open a valuation database, calculate monetary results, or persist a snapshot.

Add synthetic success and failure tests for malformed/duplicate/missing/extra
quotes, future transactions and quotes, identity/ticker/currency mismatch,
privacy-safe failure, atomic report writing, and strict JSON.

## Next step

Implement that bounded offline quote qualification boundary with synthetic data
only. Do not request the private quote JSON or execute valuation yet.

## Verification

```text
focused quote/valuation/transaction/privacy/architecture: 59 passed
full: 2,775 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
