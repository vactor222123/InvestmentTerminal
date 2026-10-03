# Phase 7 — bounded private instrument research export

Classification: `IMPLEMENTATION`. A fresh clean GitHub `develop` clone
matched `bebffba256af5fb11bd907a9ec00b20d4131afc2`. No private runtime
file, provider, or operational SQLite database was accessed or modified.

`python -m investment_terminal.cli.instrument_research_export` is a separate
read-only composition root. It requires the canonical manifest/checksum,
complete source-checkpoint directory, matching complete weekly checkpoint,
private full `LATEST_RAW_INDICATOR_PROJECTION` file and its caller-supplied
exact-byte SHA-256, existing SQLite database, one canonical selected symbol,
explicit UTC-midnight history start, explicit matching exclusive end, and
distinct private/report output paths. The projection's selected-series count,
manifest/selection/end/price-basis binding, per-item ordered identity and
weekly status must match the reconstructed plan. The selected series' latest
200 stored closes must still reproduce its projected latest timestamp/close,
sample count, SMA50/SMA200, recency proxy, and availability category.

The history window is at most 3,660 calendar days and the query accepts at
most 4,000 daily-labeled rows. Rows are sorted by timestamp, validated for
UTC, currency, finite positive OHLC, nonnegative finite volume, and OHLC
ordering. Querying holds one SQLite read-only transaction and does not call
Yahoo, overwrite candles, change checkpoints, compute recommendations, or
schedule updates. The returned historical rows are the **current SQLite
snapshot at export time**. The source SMA projection proves only latest-200
parity; it cannot prove that older SQLite rows were unchanged since the
projection was created. A deterministic checksum of the exported candle
array records the exact history included in this artifact.

Private schema-version-1 `INSTRUMENT_RESEARCH_EXPORT` contains the requested
symbol/currency, full selected indicator item, ordered OHLCV candles,
history-window and source bindings, exported candle count/checksum, and
explicit limitations. It belongs under `C:\runtime\data`. Separate
schema-version-1 `INSTRUMENT_RESEARCH_EXPORT_REPORT` contains only bindings,
source projection checksum, history-window bounds, candle count/checksum,
sample count, availability, recency proxy, status and generic failure.
It excludes symbol, currency, per-candle times/prices/volume, SMA values,
paths, and exception text. Both outputs are atomic and refuse overwrite.
If validation or either write fails, the CLI removes only its newly created
private result and attempts one generic redacted failed report. Existing
projection, weekly and candle JSON/SQLite contracts remain unchanged.

The artifact is factual research evidence, **not** verified adjusted-price
performance or exchange-session completeness. Terminal applies no explicit
corporate-action adjustment and does not establish provider historical split
semantics. Do not send the private artifact to ChatGPT automatically. The
next gate is one exact-baseline private, user-executed qualification of a
known selected instrument, returning only the redacted report, its SHA-256,
and independent SQLite integrity. A broader query/export interface,
portfolio integration, automatic sharing, and weekly scheduling remain
outside this package.
