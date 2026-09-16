# Phase 7 Package 153 — No-Price Terminal Isolation

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ b298ca9ee4d99e66051d8c8c2d60240ea35d2bff
```

## Result

Private resumable checkpoint schema 4 is implemented. Every newly caught
importer failure records the existing stable Yahoo category and bounded,
allowlisted causal exception-type chain before the atomic checkpoint write.
Schemas 1–3 remain readable, and legacy failed evidence is represented as null
only when another item causes a schema-4 write; an exact legacy resume does not
rewrite the checkpoint.

The separate `REPRODUCED_YAHOO_NO_PRICE_DATA_V1` transition is implemented as
an offline manifest-bound service and CLI. It verifies strict UTF-8 JSON bytes
against the supplied SHA-256 and requires exact manifest, request, window,
partial-selection, stored `APIError`, `FAILED/NO_PRICE_DATA`, null coverage,
and recognized yfinance missing-price causal evidence. It changes only the one
failed outcome to `FINAL_FAILED`, preserves missing request members, rejects
conflicts before writing, and supports exact idempotent repeat.

The CLI writes the private checkpoint atomically before the redacted schema-1
transition report. A checkpoint-write failure cannot claim success; a report-
write failure after commit can be reconciled through the exact repeat.

Existing numeric/OHLC terminal isolation, public batch/report schemas,
`Candle`, and SQLite remain unchanged. This package did not read or modify
private runtime inputs, contact Yahoo, open SQLite, resume the sweep, or execute
batch 107.

## Verification

- focused checkpoint, transition, CLI atomicity, consumer, and failure-path
  tests: 58 passed;
- complete suite: 3,094 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

## Next Gate

Run exactly one controlled offline transition for batch 106 using the existing
private manifest/checkpoint and immutable Package 151 qualification bytes plus
their SHA-256. Return only the redacted transition report. Do not contact Yahoo,
open SQLite, resume collection, ingest the 13 missing items, or execute batch
107 until that report is reviewed.
