# Phase 7 — bounded latest raw-close indicator projection

Classification: `IMPLEMENTATION`. A fresh clean GitHub `develop` clone
matched caller baseline `26f2831251175f7b221e09393d2fa209800d1684`.

The existing Yahoo candle adapter requests `auto_adjust=False` and stores
the provider `Close` value in the daily candle table. It does not persist
`Adj Close`, split factors, or distribution adjustments. The existing
`TechnicalAnalysisService` computes SMA50/SMA200 for one asset but is not a
batch projection and also produces interpretive trend classifications.
Therefore this package exposes only explicitly labeled averages of the
**stored Close without a Terminal-side adjustment**. They are objective
arithmetic over the stored sample, not verified corporate-action-adjusted
performance or investment advice. The upstream provider's historical split
handling is not inferred from `auto_adjust=False`.

`python -m investment_terminal.cli.latest_raw_indicator_projection` now
reconstructs the manifest/source success selection and requires a complete
matching weekly checkpoint. It reads existing SQLite daily candles under one
read-only transaction at an explicit exclusive UTC end. `--max-items` bounds
the deterministic prefix of the selected series (1 through the selection
size). For each selected series, at most the latest 200 pre-end raw closes
are used. The operation rejects invalid timestamp/currency evidence and
non-finite or non-positive sampled closes. SMA50 requires 50 rows; SMA200
requires 200. It records the latest timestamp, latest raw close, capped
sample count, currency, weekly status, seven-calendar-day recency proxy,
and one explicit availability category. No Yahoo request, candle write,
checkpoint write, gap repair, or scheduler is involved.

The schema-version-1 `LATEST_RAW_INDICATOR_PROJECTION` JSON is private: it
contains identities and values, and belongs under `C:\runtime\data`.
The separate schema-version-1
`LATEST_RAW_INDICATOR_PROJECTION_REPORT` is redacted: it contains only
manifest/selection/end/price-basis bindings, budget and selected/processed
counts, availability counts, SMA availability counts, and the recency-proxy
count. Existing weekly checkpoint and coverage report schemas are unchanged.
Both files use atomic writes. If either write fails, newly created output
files are removed and the CLI returns failure; a generic redacted failed
report is attempted without private exception text. Existing destinations
are never overwritten.

These values do **not** establish exchange-session completeness, continuous
ten-year history, adjusted-price validity across corporate actions, or
fitness for return analysis. The price basis must remain visible to any
future ChatGPT-facing export. The next package should prepare one exact-
baseline private operational qualification with `--max-items 1`, check its
redacted report and SQLite integrity, then decide whether a complete
projection is safe. Do not schedule weekly execution or treat raw SMA values
as final adjusted indicators before that measurement and a separate
corporate-action policy.
