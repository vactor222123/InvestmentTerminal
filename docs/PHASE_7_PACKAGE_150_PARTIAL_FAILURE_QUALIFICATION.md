# Phase 7 Package 150 — Partial Failure Qualification

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ 0f044346824a91e677fa8cb3a788a52d74082420
```

## Result

Package 150 implements the read-only failure-observability boundary selected by
Package 149 and corrects the collection sweep's current-run deferred aggregate.
It does not change checkpoint schema 3, the private checkpoint, SQLite, the
existing exact-coverage diagnostics, or provider retry behavior.

`ManifestPartialFailureQualificationService` accepts one manifest-bound proper
partial checkpoint. Before provider access it requires non-empty outcome keys
that are an exact subset of the request, at least one missing request item,
exactly one `FAILED` outcome, and failure type exactly `APIError`. It internally
selects that private item; missing items can never become candidates.

The service makes one call through the production Yahoo candle-projection API
over the manifest's exact resolution, currency, and half-open window. It has no
repository, database, importer, or checkpoint writer. Returned candles are
validated against request identity, time bounds, uniqueness, and order, then
discarded after aggregate evidence is built.

## Report Contract

The schema-version-1 `MANIFEST_PARTIAL_FAILURE_QUALIFICATION` report binds:

- manifest checksum, batch index/count, and request checksum;
- original requested start/end;
- aggregate requested, checkpoint, missing, failed, and selected counts;
- `QUALIFIED`, `EMPTY`, or `FAILED` status;
- candle count and typed omission evidence for a returned projection;
- existing stable Yahoo failure category and bounded allowlisted exception type
  chain for a failed request.

It excludes symbol, currency, price, path, provider text, exception message,
raw row, and candle value. A repeated request measures current provider
behavior; it cannot reconstruct the original batch-106 exception cause and
does not authorize ingestion or checkpoint mutation.

The CLI validates manifest and checkpoint evidence before constructing the
live Yahoo client, atomically writes only the redacted report, and exits nonzero
for `FAILED`.

## Deferred Counter Correction

`current_run.deferred_failure_count` now counts only newly written `FAILED`
outcomes whose type is exactly `YahooCandleInvalidResponseError`. A stopping
`APIError`, timeout, persistence error, or other systemic failure reports zero.
The schema-version-1 contract and ending-coverage semantics are unchanged.

## Failure Paths

Tests cover manifest/checkpoint mismatch before provider access, empty and
complete checkpoints, ambiguous or non-API failures, mismatched projection
identity/window, local candle rejection, rate limiting with causal type chain,
empty projection, privacy, non-mutation, CLI failure envelopes, and the Package
148 systemic-halt counter shape.

## Next Gate

Run exactly one user-executed qualification for batch 106 against its existing
private partial checkpoint. Return only the redacted report. Do not send the
manifest, checkpoint, cache, or any private values; do not run the sweep, write
SQLite, retry ingestion, or permit batch 107 until the result is reviewed.
