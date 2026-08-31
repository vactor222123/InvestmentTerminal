# Phase 7 Package 70 - Single-Series Raw Candle Diagnostic

## Classification

IMPLEMENTATION.

## Audit conclusion

The 86 measured `RESPONSE_NUMERIC` outcomes are not missing-price evidence.
They mean that at least one raw Yahoo OHLCV value failed the production
finite/positive numeric contract. The production adapter intentionally stops at
the first invalid value, so the existing redacted eligibility report cannot
identify the affected row or distinguish non-finite, non-positive, non-real, or
negative values.

## Result

The new bounded diagnostic automatically selects the first deterministic
schema-version-3 checkpoint outcome whose terminal category is
`RESPONSE_NUMERIC`. It repeats only that series over the checkpoint's unchanged
90-day window using the exact production Yahoo history options and inspects the
raw frame without weakening or bypassing production candle validation.

The schema-version-1 redacted report contains aggregate valid/invalid row
counts, stable invalid-reason counts, and affected UTC timestamps with reason
labels. It excludes instrument identities, prices, volumes, paths, provider
text, and exception messages. The private universe and checkpoint are read-only;
the command performs no scan, migration, ranking, candle persistence, or batch
generation.

## Next step

Run the diagnostic once against the existing private universe and schema-3
checkpoint, using the unchanged window end. Return only the redacted report.
Do not run slice 002 or another diagnostic before this result is reviewed.
