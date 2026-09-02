# Phase 7 Package 83 — Symbol-Currency Diagnostic

## Classification and Baseline

Classification: `IMPLEMENTATION`.

Fresh `develop` clone verified exactly at
`a96c1c26f190f7ce322492fe096b652acf2cca3e`.

## Result

This package adds one read-only diagnostic for the first deterministic private
terminal `INVALID_CURRENCY` outcome. It verifies the eligibility-success
projection and qualification request/checkpoint checksums, repeats exactly one
Yahoo symbol search, and does not modify the checkpoint.

The schema-version-1 redacted report records only total and exact-match row
counts plus currency-field shape counts: missing, null, empty, non-string,
invalid format, and valid format. It also records the count of distinct valid
currency values without exposing those values. Symbols, currencies, paths,
provider text, and exception messages are excluded. Failures produce a
redacted non-zero report.

No broader currency scan, batch construction, candle retrieval, persistence,
analysis, or trading is authorized.

## Next Step

Run the diagnostic once against the existing private projection and currency
checkpoint, then return only its redacted report.
