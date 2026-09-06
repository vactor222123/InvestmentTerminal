# Phase 7 Package 112 — Typed Yahoo Candle Projection

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`53212f8f9343bc22a607ebb15d51fa01a5c90a05`.

This package implements the typed provider-frame boundary selected by Package
111 without changing the existing list-returning client contract or enabling
batch remediation prematurely.

`YahooCandleProjection` contains immutable candles, an explicit omitted-
trailing count, and typed omission categories. `get_candle_projection` uses the
same provider request options as production and retains strict validation by
default. Existing `get_candles` delegates to strict projection and therefore
preserves its public behavior.

The explicit daily-only trailing policy validates required columns and every
timestamp before row projection. Timestamps must be UTC-normalizable, unique,
and strictly ascending. It permits exactly one final row only when at least one
preceding candle is valid and the final row's only defects are non-finite OHLCV
numbers. It emits `TRAILING_NON_FINITE_NUMERIC` evidence.

Interior or multiple invalid rows, non-real values, non-positive OHLC, negative
volume, inconsistent finite OHLC, invalid/duplicate/unordered timestamps,
missing columns, no valid predecessor, and weekly/monthly trailing defects all
remain hard failures.

The manifest batch path is deliberately unchanged. Its generic list-only
historical service cannot yet carry omission evidence into the private
checkpoint and redacted report. The next package must audit the smallest typed
service/checkpoint propagation seam. Batch 19 retry and later batches remain
blocked until propagation is explicit and tested.

Verification:

- focused Yahoo/raw/service/architecture checks: 58 passed;
- complete local suite: 2,991 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
