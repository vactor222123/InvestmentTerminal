# Phase 7 Package 15 — Measured-State Refresh Audit

Baseline: `develop @ 59a89b4d2c5c315fc74bd065ab8ea762a2c1fbcd`.

This audit re-ran the existing read-only operational baseline against the
populated market SQLite after controlled MSFT, AAPL, and IBM completion. The
result contains three deterministic daily USD series and 3,762 total candles:

| Identity | Count | Earliest | Latest |
|---|---:|---|---|
| `AAPL:D:USD` | 1,254 | `2021-08-19T04:00:00Z` | `2026-08-18T04:00:00Z` |
| `IBM:D:USD` | 1,254 | `2021-08-19T04:00:00Z` | `2026-08-18T04:00:00Z` |
| `MSFT:D:USD` | 1,254 | `2021-08-19T04:00:00Z` | `2026-08-18T04:00:00Z` |

The report is stored outside source control as
`phase7_measured_baseline_after_ibm.json`, with SHA-256
`9e52b8844a8c40fd4b53af2c11c34dca3bf0b392d5b6ebcde58a1b107112cfc8`.

The measured gap is explicit:

```text
per-series freshness: UNMEASURED
refresh_observability: UNMEASURED
measured_performance: UNMEASURED
```

The repository already contains `MarketDataFreshnessService` and
`MarketDataRefreshService`, including bounded stale overlap and before/after
freshness evidence. It does not contain a dedicated CLI that composes those
services into an atomic operational report. Existing portfolio-ranking
composition is not a substitute for a bounded operational refresh contract.

## Selected next package

Add one versioned, deterministic single-instrument refresh-observability CLI
and atomic JSON report. It should accept explicit symbol, resolution, currency,
checked-at, database, cache, and output values; preserve freshness before and
after, the exact import result, duration, and visible failure; and fail closed.

The package must include hermetic success, already-fresh, and provider or
persistence failure paths. Multi-instrument refresh, scheduling, retries,
universe ingestion, analysis, and trading remain out of scope. A live run must
start with one already measured instrument and be reviewed before expansion.

Verification:

```text
focused: 66 passed
full: 2,726 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
