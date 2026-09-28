# Phase 7 — explicit-window stored history span

Classification: `IMPLEMENTATION`; private operational run pending. Fresh clean
`develop` baseline: `b76220fe7bfcd6ae9d1d052f2e2a22c3b5998ac4`.

The returned schema-1 weekly stored-coverage report binds the completed
2026-09-23 checkpoint and records 17,300,242 daily rows across 11,892
selected series. All have at least one row; 11,566 have at least 50 and
10,221 have at least 200; 245 lack a candle in the last seven calendar days.
The 214 weekly failures remain 42 `NO_PRICE_DATA`, 140 `RESPONSE_NUMERIC`,
and 32 `STORED_CANDLE_DRIFT`. The user reported SQLite integrity `ok`.
These counts do not establish ten-year coverage or exchange-session quality.

The existing `weekly_stored_coverage` CLI now accepts an optional explicit
UTC-midnight `--history-start`. Omission preserves the exact schema-1 JSON
shape. Supplying it emits schema 2 bound to the same manifest, complete source
and weekly checkpoints, exclusive end, and a new `history_start` field. The
additional aggregate fields count rows and empty series inside the half-open
window, series with a first/last candle within seven calendar days of its
boundaries, series satisfying both endpoint proxies, and series/event counts
for consecutive-candle gaps over seven and over 30 calendar days. Identities,
prices, currencies, paths, and per-series dates remain excluded. An invalid
start or selected timestamp/currency fails closed into a redacted report.
SQLite opens read-only and one read transaction holds a consistent snapshot
during the long scan; no Yahoo request or candle/checkpoint mutation occurs.

Gap thresholds are **calendar-day diagnostics only**. Weekends, holidays,
trading halts, late listings, and delistings can explain missing endpoints or
long intervals. These metrics cannot assert actual missing exchange sessions,
corporate-action-adjusted correctness, or computed SMA values. Do not retry
market acquisition or enable a scheduler from this report alone.

Next operational gate: one private, read-only invocation with
`--history-start 2016-09-23T00:00:00+00:00` and the already completed weekly
checkpoint ending `2026-09-23T00:00:00+00:00`. Return only the new redacted
schema-2 report and separate SQLite integrity result. Review the aggregate
result before any targeted quality work.
