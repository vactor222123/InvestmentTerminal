# Phase 7 Package 114 - Versioned Omission Evidence Path

## Classification

`IMPLEMENTATION`

Source baseline was verified exactly at
`develop @ 7bff11ac95aa6057390215d4f3cc17a81b71c1aa` in a fresh clone.

## Result

The manifest execution path now uses a separate projected historical importer.
It may accept the Package 112 daily trailing-incomplete projection, persists
only validated candles, and returns explicit omission evidence. Generic
historical import and refresh remain strict.

The durable evidence path is versioned end to end:

- checkpoint schema 2 stores `omitted_trailing_count` and `omission_types` per
  outcome;
- legacy schema-1 checkpoints migrate in memory with explicit zero omission;
- resumable reports use schema 3 and expose current/cumulative omission totals;
- manifest-bound and drain reports use schema 2;
- drain aggregation preserves omission totals and distinct reason types.

Only zero or one omission with the exact type
`TRAILING_NON_FINITE_NUMERIC` is accepted. Inconsistent checkpoint or importer
evidence fails closed. Provider, persistence, and checkpoint failures remain
visible; reports contain no symbols, paths, prices, provider text, or exception
messages.

## Scope boundaries

This package does not change Yahoo's strict legacy list contract, generic
refresh, weekly/monthly handling, universe membership, analysis, scheduling, or
trading. It performs no live provider request and does not modify private
runtime data.

## Verification

- focused projection/batch/CLI/strict-boundary/architecture tests: 97 passed;
- complete suite: 2,996 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next evidence gate

Run one controlled manifest batch-19 retry against the existing private
checkpoint. Review only its redacted report. Do not execute batch 20 until the
retry proves success with coherent omission evidence and SQLite integrity.
