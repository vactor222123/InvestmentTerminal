# Phase 7 Package 20 — Refresh-Report Projection

Source baseline: `develop @ e151a457ff8869119195c0ad03c7e0e7729a7613`.

This package implements the optional, read-only projection selected by Package
19. `OperationalDataBaselineInputs` and the CLI accept an explicit refresh
report path. When omitted, baseline schema version 1 preserves its exact
eight-store inventory. When supplied, one deterministic `REFRESH_REPORT` store
is appended and sorted with the existing stores.

The projection validates schema version, Yahoo provider identity, normalized
request identity, aware request/start/completion timestamps, non-negative
finite duration, supported status, result/failure consistency, request/result
identity agreement, booleans, and non-negative consistent transfer counters.
Valid `SUCCESS`, `NOT_READY`, and `FAILED` reports are measured operational
evidence. A valid failure does not invent result counters or readiness facts.
Malformed, unsupported, or inconsistent input remains a visible `ERROR` store
and cannot make refresh observability or measured performance `READY`.

Only aggregate identity, timing, status, attempt/readiness flags, and transfer
counters are projected. Database contents, failure details, provider secrets,
freshness internals, and source report contents are not copied into the
baseline. The package performs no refresh, scheduling, multi-instrument
aggregation, analysis, or trading.

Read-only operational verification against
`C:\runtime\reports\market_data_refresh_msft.json` produced:

```text
schema_version = 1
store_count = 9
REFRESH_REPORT = READY
identity = YAHOO_FINANCE:MSFT:D:USD
status = SUCCESS
duration_seconds = 1.149708
downloaded / inserted / duplicates = 10 / 4 / 6
refresh_observability = READY
measured_performance = READY
```

Verification:

```text
focused baseline/refresh/architecture: 44 passed
full: 2,743 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```

Next: perform a focused Phase 7 closure-readiness audit before selecting any
new instrument, scheduler, or mass-refresh package.
