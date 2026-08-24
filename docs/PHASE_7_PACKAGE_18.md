# Phase 7 Package 18 — MSFT Already-Fresh Provider Bypass

Baseline: `develop @ 513cc311eea795ed63a7be74adf258c66951681f`.

The live MSFT refresh command was repeated with the exact original checked-at
value, `2026-08-24T19:00:58.995247Z`, and a separate output path. The report
completed with `SUCCESS` in 0.001261 seconds.

Measured repeat result:

```text
freshness before: FRESH
freshness after: FRESH
refresh attempted: false
downloaded: 0
inserted: 0
duplicates: 0
import: null
failure: null
```

Read-only inspection confirmed the database remained unchanged: 1,258 MSFT
daily candles through `2026-08-24T04:00:00Z`, 3,766 total market candles, and
SQLite integrity `ok`.

The repeat report remains outside source control at
`C:\runtime\reports\market_data_refresh_msft_repeat.json`. Its SHA-256 is
`5cc4840c343eeec9a997eb99592c524dc3120f9ec531ee00b3f88ac7f98c9d3a`.

This confirms the already-fresh provider-bypass path for one explicit MSFT
request. The canonical operational baseline still has no refresh-report input
and therefore cannot project these measured refresh outcomes or duration;
`refresh_observability` and `measured_performance` remain `UNMEASURED` there.
The next package should audit the smallest backward-compatible projection of
one explicit refresh report into that baseline. Another instrument,
scheduling, and mass refresh remain out of scope.

Verification:

```text
focused: 71 passed
full: 2,731 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
