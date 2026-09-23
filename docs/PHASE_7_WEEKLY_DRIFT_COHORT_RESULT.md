# Phase 7 — Weekly Drift-Cohort Result and Continuation Gate

Classification: `AUDIT`. The fresh clean `develop` clone matched the caller's
exact `92e28ce408e8d6b48869dfd44e10fc31f9981f63` baseline. Only the
returned schema-version-2 redacted diagnostic was reviewed; no private
checkpoint, database, or individual candle was inspected or changed.

The report binds manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and selection checksum
`75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`
to the exclusive 2026-09-23 UTC end. Status was `COMPLETE`: nine of nine
checkpointed drifts were attempted, with zero remaining, inconclusive, or
provider-failed diagnostics. All nine currently reproduced volume-only
differences. Across 54 compared overlap rows, nine rows differed; only the
`volume` field changed. The current responses also contained 90 new candles
and nine omitted trailing rows. The diagnostic did not persist those candles.

This establishes a current volume-only pattern for this exact cohort, not the
cause of the earlier provider revision, a stable future provider policy, or
complete price history for these nine series. The prior 120-series weekly
checkpoint still contains nine `STORED_CANDLE_DRIFT`, twelve
`RESPONSE_NUMERIC`, and three `NO_PRICE_DATA` failures. Its nine drift outcomes
are terminal for this checkpoint: `WeeklyCandleRefreshService.run` skips every
symbol already in `outcomes`. The same service isolates non-rate-limited
per-series failures and can continue with the 11,772 never-attempted series;
it does not require a persistence-policy change to collect those other series.

Next operational gate: run one existing, checkpoint-resuming weekly refresh
with `--max-items 1000` and the unchanged 2026-09-23 exclusive end. Review its
redacted aggregate report and read-only SQLite integrity before increasing
the budget. Do not replace stored volume, reopen the nine failures, or claim
all-series freshness in that run.

A later implementation package may admit volume-only overlap revisions while
preserving stored OHLCV and inserting only new rows. That requires an explicit
versioned checkpoint/report field for observed volume drift and a separate
evidence-bound treatment of already terminal drift outcomes. Price, currency,
identity, and window drift must still fail closed. It must test provider,
persistence, checkpoint-write, and repeat paths before operational use.
