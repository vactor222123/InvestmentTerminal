# Phase 7 Package 17 — Live MSFT Refresh Measurement

Baseline: `develop @ 6ed92f05d92d0fa0431ba743f27695c68e48051d`.

One explicit live MSFT daily refresh ran at
`2026-08-24T19:00:58.995247Z`. The schema-version-1 report completed with
`SUCCESS` in 1.149708 seconds.

Measured freshness transition:

```text
before status: STALE
before last session: 2026-08-18
expected session: 2026-08-21
refresh attempted: true
downloaded: 10
inserted: 4
duplicates: 6
after status: FRESH
after last session: 2026-08-24
stored MSFT total: 1,258
```

Read-only post-run inspection confirmed 1,258 MSFT daily candles from
`2021-08-19T04:00:00Z` through `2026-08-24T04:00:00Z`, 3,766 candles across
the market store, and SQLite integrity `ok`.

The operational report remains outside source control at
`C:\runtime\reports\market_data_refresh_msft.json`. Its SHA-256 is
`b05997305236ccf463060bbdab5908645beda7fc7713f9926bcdc83090570b9f`.

This establishes one measured stale-to-fresh transition only. The next bounded
action is an exact repeat with the same checked-at value and a separate output
path to confirm the already-fresh provider-bypass path. Another instrument,
scheduling, and mass refresh remain out of scope.

Verification:

```text
focused: 69 passed
full: 2,731 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
