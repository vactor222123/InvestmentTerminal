# Phase 7 Package 111 — Trailing Incomplete Candle Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`4b44eaaa677cafc8080aec5c897e7ce091ed923c`.

## Current behavior

`YahooFinanceClient` validates every provider row and rejects the complete
series on the first invalid timestamp, numeric value, or OHLC relationship. It
does not validate that the raw index is unique and strictly ascending before
using row position. It supports daily, weekly, and monthly requests.

The raw diagnostic analyzer identifies numeric and OHLC defects, but its Yahoo
adapter currently always requests `1d`. That matches the failed batch-19 daily
request. It would not be valid evidence for a future weekly or monthly failure.

The current public client contract returns only `list[Candle]`; it has no
durable field for recording an omitted provider row. Therefore a broad or
unobservable invalid-row filter is rejected.

## Future-scenario policy

Any remediation must remain fail-closed for:

- an invalid interior row;
- two or more invalid rows, including multiple trailing rows;
- missing required columns or an invalid frame type;
- non-datetime, duplicate, or non-ascending timestamps;
- non-positive OHLC, negative volume, or inconsistent high/low values;
- a frame with no preceding valid candle;
- weekly/monthly requests until raw diagnosis uses the matching interval;
- empty, newly listed, delisted, corrected, or later-restated series without
  inventing coverage or prices.

Only one daily row may qualify as trailing incomplete evidence when all of the
following are proven in order: required columns exist; every timestamp is
UTC-normalizable, unique, and strictly ascending; every preceding row is fully
valid; the final row is the sole invalid row; and its only defects are one or
more non-finite OHLCV numeric values. Timestamp, sign, OHLC-consistency, shape,
and interior defects remain hard failures.

## Selected implementation boundary

Add one deterministic Yahoo-frame projection seam used by the production
client. It must validate the complete frame before projection, preserve the
existing strict behavior by default, and enable the bounded daily-only trailing
incomplete policy explicitly. It must expose typed omission evidence to the
caller rather than silently treating the provider row as a valid candle.

The first implementation package must cover the current batch path without a
project-wide rewrite: one typed projection result, production-client
integration, and focused tests for every rejection above. Batch checkpoint and
report propagation must be explicit; if the existing list-only service seam
cannot carry omission evidence without ambiguity, implementation must stop at
that boundary rather than hide it.

No batch retry or batch 20 execution is authorized by this audit.

Verification:

- focused Yahoo/raw/diagnostic/batch/service/architecture checks: 61 passed;
- complete local suite: 2,977 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
