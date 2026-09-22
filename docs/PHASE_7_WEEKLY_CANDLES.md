# Phase 7 — Weekly Daily-Candle Refresh

This package adds an operational refresh path after ten-year manifest collection.
It does not reopen the residual 11 collection defects or broaden the universe.
The source is the canonical manifest plus its complete, request-bound collection
checkpoints. Only source `SUCCESS` daily series are selected; `EMPTY`, `FAILED`,
and `FINAL_FAILED` remain excluded.

`python -m investment_terminal.cli.weekly_candle_refresh` accepts the manifest,
checksum, source checkpoint directory, existing candle SQLite database, Yahoo
cache directory, separate private weekly checkpoint, redacted report path,
UTC-midnight exclusive `--end`, and `--max-items`. End must be no later than the
last completed UTC day. One invocation processes a bounded subset; rerun with
the same end and checkpoint to finish remaining series without refetching
completed identities. Use a new weekly checkpoint and report for each later
end. The operator can schedule this command weekly after controlled live
qualification; this package does not install a scheduler or run on private data.

Each series requests from seven days before its latest stored daily candle to
the exclusive end. A gap over 90 days is reported as `WINDOW_TOO_LARGE`, not
silently skipped. Returned candles must match symbol, resolution, currency,
and time window; overlap value drift is reported as `STORED_CANDLE_DRIFT`
without overwriting SQLite. Valid new rows use existing atomic
`CandleRepository.save_many` insert-or-ignore persistence. The private
checkpoint is atomically replaced after each series. A failed write is surfaced;
if a process dies after SQLite commit but before checkpoint write, rerun is
idempotent on existing rows. A Yahoo rate limit halts; other per-series failures
do not block unrelated series. Failed series may be retried in a later weekly
run, not automatically in the same checkpoint.

The redacted report contains counts, checksums, timing, and stable categories,
never identities, prices, currencies, paths, provider text, or exceptions.
`indicator_200_ready_count` is only a stored-row-count precondition, not
trading-session completeness or freshness proof. Downstream code reads sorted
candles through `CandleRepository.get_range` and can pass them to
`TechnicalIndicators.sma`, `ema`, and other calculators. Portfolio
interpretation and trading remain outside Terminal.

Before operational use, locate the actual private manifest, all 601 collection
checkpoints, and SQLite path on the user's machine; do not invent them. Run a
one-item qualification, inspect the redacted report and SQLite integrity,
then run a bounded full drain and repeat-idempotency check. Compare real
session coverage separately before claiming a complete analytical universe.
