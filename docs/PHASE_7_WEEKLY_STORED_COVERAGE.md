# Phase 7 — offline weekly stored-coverage audit

Classification: implementation and local qualification; private operational run pending.
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

The count bins and seven-day proxy do not prove exchange-session coverage,
corporate-action-adjusted prices, data quality of OHLC, or computed SMA
values. Do not activate unattended weekly scheduling or claim analysis-ready
coverage from this report alone. The next operational step is one private
read-only run with the existing manifest, source checkpoint directory,
complete weekly checkpoint, and SQLite database; return only the redacted
report plus a separate SQLite integrity result. Review aggregate gaps before
selecting a bounded quality-remediation package.
