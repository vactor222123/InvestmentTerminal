# Phase 7 Package 87 — Resumable Chart Currency

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`267cbc6135e501cd56f3d52de9443a9360d3fecd`.

The resumable symbol-currency operation now owns schema version 2 and obtains
explicit currency directly from Yahoo chart metadata. Existing schema-version-1
checkpoints migrate atomically before provider access. Migration preserves all
outcomes and reopens only terminal `INVALID_CURRENCY`; successes and unrelated
terminal failures remain terminal.

The existing maximum of 100 items per invocation, three-attempt cap, immediate
rate-limit halt, atomic private checkpoint, and aggregate-only redacted report
remain unchanged. The operation does not infer currency, generate market-data
batches, retrieve candles, ingest data, analyze investments, or trade.

Next: execute one controlled `--max-items 1` run against the existing private
projection and checkpoint, then return only the redacted report for review.
