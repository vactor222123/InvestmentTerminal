# Phase 7 — offline weekly stored-coverage audit

Classification: implementation and local qualification; private operational
schema-1 run subsequently completed.
Baseline: `eacc9990601ed1084c801e950a2a0b04350eedcb` on `develop`.

The completed 2026-09-23 weekly checkpoint records 11,892 attempted selected
daily series. Its latest redacted report shows 11,678 successes and 214
isolated failures (42 `NO_PRICE_DATA`, 140 `RESPONSE_NUMERIC`, 32
`STORED_CANDLE_DRIFT`); the user reported SQLite integrity `ok`. Those
figures describe refresh outcomes, not the completeness of ten-year stored
histories. The reported 200-row indicator-readiness figure is a sample-size
test only.

`python -m investment_terminal.cli.weekly_stored_coverage` adds an offline,
read-only aggregate measurement. It validates the manifest, all source
checkpoints, and a complete, bound weekly checkpoint. SQLite opens with
`mode=ro` and `query_only`; no provider, cache, or candle writes occur. The
schema-1 JSON report contains only aggregate series/row bins, 50/200 sample
readiness, a seven-calendar-day latest-row proxy, and weekly outcome counts.
It excludes symbols, currencies, prices, paths, per-series dates, and raw
exception text. Any invalid selected timestamp or currency fails closed.

The returned private schema-1 report records 17,300,242 daily rows,
11,566 series with at least 50 rows, 10,221 with at least 200, and 245
without a candle in the final seven calendar days. The user reported SQLite
integrity `ok`. See `docs/PHASE_7_TEN_YEAR_STORED_SPAN.md` for the separate
explicit-window follow-up.

The count bins and seven-day proxy do not prove exchange-session coverage,
corporate-action-adjusted prices, data quality of OHLC, or computed SMA
values. Do not activate unattended weekly scheduling or claim analysis-ready
coverage from this report alone. Review explicit-window aggregate gaps before
selecting a bounded quality-remediation package.
