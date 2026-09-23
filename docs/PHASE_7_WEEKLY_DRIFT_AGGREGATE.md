# Phase 7 — Complete Weekly Drift-Cohort Diagnostic

Classification: `IMPLEMENTATION`. Fresh `develop` HEAD exactly matched
`352a5a3feab3450f305980fc488db73a5f16e9f1` with a clean worktree.

The first read-only diagnostic reproduced one of nine checkpointed drifts. One
of six overlap candles had a different `volume`; Open, High, Low, and Close
matched. Ten current candles were new and one incomplete trailing row was
omitted. No stored candle or weekly checkpoint was changed. This one result
does not prove that the other eight drifts are volume-only.

The existing `weekly_candle_drift_diagnostic` CLI now accepts optional
`--max-items`. The default `1` preserves the schema-version-1 single-series
contract. A larger value must equal the complete checkpointed drift count and
the cohort must contain at most 20 outcomes. The schema-version-2 aggregate
mode validates the same manifest, complete source checkpoints, and private
weekly checkpoint, then compares each selected drift in manifest order. It
stops immediately on a provider rate limit. Other provider failures are
counted separately, without identity-level results.

The aggregate report records counts of reproduced, no-longer-reproduced,
inconclusive, and provider-failed series; volume-only versus non-volume-only
reproduced series; total changed overlap rows; a histogram of changed fields;
and bounded omission counts. It contains no symbols, prices, currency values,
per-series candle timestamps, paths, provider text, or exception messages. SQLite is opened
with `PRAGMA query_only = ON`; candles and checkpoints are never written.
Only Yahoo cache and the separate redacted report may be written.

Next, run `--max-items 9` once on the existing private weekly checkpoint and
return only its redacted report. Do not apply a volume-only policy, change
stored candles, or launch the remaining 11,772 weekly series before the
aggregate field evidence is reviewed.
