# Phase 7 Package 117 - Projection Decision-Parity Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`ab0fd0621f0422ad52ff6dcd67bd638defb3f462`.

## Finding

The manifest diagnostic and production projection fetch the same Yahoo history
shape, but they do not evaluate it through one decision contract.

Production normalizes every timestamp, requires unique strictly ascending
order, validates preceding candles, requires the invalid row to be final, and
checks sign plus partial finite-OHLC consistency before allowing the one
daily non-finite omission. The raw analyzer reports invalid values and checks
OHLC consistency only when every required numeric field is valid. It does not
report timestamp structure, invalid-row position, or the partial finite-OHLC
decision. The schema-2 batch report then retains only the exception class.

Consequently, Package 116 proves two rows with one `CLOSE_NON_FINITE` defect but
cannot distinguish an ordering, position, predecessor, or partial-OHLC
rejection. Repeating ingestion or weakening validation would not resolve this
evidence gap safely.

## Selected boundary

Implement one provider-owned typed trailing-incomplete assessment and make the
production projection and manifest diagnostic use that same assessment on the
same in-memory frame. The assessment must have a stable policy identity and a
closed rejection-reason vocabulary covering timestamp normalization,
uniqueness/order, invalid-row multiplicity/position, valid predecessor,
non-finite-only numeric policy, sign, and partial OHLC consistency.

The manifest diagnostic alone advances to schema version 2 and exposes only:

- policy identity;
- `ELIGIBLE` or `REJECTED`;
- one stable rejection reason or null;
- omitted trailing count and omission types when eligible.

It must not expose the valid timestamp, row ordering values, symbol, currency,
prices, volumes, provider text, paths, or exception messages. The generic raw
analyzer and its eligibility diagnostic remain schema version 1. The operation
stays read-only: no SQLite, checkpoint writer, import, retry, or later-batch
authority.

## Required tests

Focused tests must prove parity for eligible final non-finite rows and every
rejection class, one provider request, unchanged strict legacy projection,
unchanged single-series report shape, schema-2 manifest success/failure reports,
and redaction. Architecture guards and the complete suite remain mandatory.

## Next action

Implement this bounded parity seam. Do not run batch 19, batch 20, or the drain
until implementation and failure-path tests pass.

## Verification

- focused Yahoo/raw/manifest/architecture tests: 64 passed;
- complete suite: 2,996 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
