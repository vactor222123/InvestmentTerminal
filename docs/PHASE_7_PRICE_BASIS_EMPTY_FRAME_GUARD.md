# Phase 7 — price-basis empty-frame guard

Classification: `IMPLEMENTATION`. A fresh clean `develop` clone matched
`d438e357863bbbeb48be77888257efdf0d1c3220` before edits.

The user deferred the live Yahoo price-basis qualification. No Yahoo request,
private runtime file, SQLite database, or existing candle was accessed or
changed in this package.

Static review found one concrete classification defect in the new isolated
qualifier: pandas `DataFrame.empty` is true both for zero rows and for a frame
with rows but zero columns. The latter response had been reported as `EMPTY`,
masking a malformed provider shape. The guard now considers only zero rows
empty. A row-bearing columnless frame reaches required-`Close` validation and
reports `MALFORMED` / `CLOSE_MISSING` with its aggregate row count. All other
schema-1 report fields and the existing Yahoo ingestion remain unchanged.

Focused failure-path coverage exercises the distinction. The live
one-instrument request remains paused; do not infer adjusted-price semantics
or modify storage from local fake-provider tests. When the user chooses to
resume, run only the bounded command in
`PHASE_7_YAHOO_PRICE_BASIS_FIELD_QUALIFICATION.md` and review its redacted
report before selecting any price/action provenance design.
