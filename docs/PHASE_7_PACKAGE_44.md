# Phase 7 Package 44 - Split OpenFIGI Ticker Failure Categories

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ 278bd5e601fd576e80994c6a6094b7d4641d0e0e`.

## Result

The redacted OpenFIGI operational report advances to schema version 3. The
former combined `TICKER_MISMATCH_OR_AMBIGUOUS` outcome is replaced by
`CANDIDATE_TICKER_ABSENT` and `CANDIDATE_TICKER_WITH_ALTERNATIVES`.

Ticker confirmation still fails closed in both cases. No alternate listing is
selected, no first-row assumption is introduced, and successful matching still
requires the provider ticker set to equal the single candidate ticker. The
report exposes only the category, never ticker values, counts of alternate
tickers, response text, identities, FIGIs, paths, or credentials.

All other failure categories, aggregate coverage fields, exact-byte private
archives, and atomic metadata publication remain unchanged.

## Scope

This package uses synthetic clients only. It does not inspect or parse the
private operational archive, rerun OpenFIGI, qualify quotes, create valuation,
or authorize trading.

## Verification

```text
focused OpenFIGI/metadata/architecture checks: 42 passed
full: 2811 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```

## Next step

After push, run one controlled schema-version-3 bootstrap with a unique run ID
and return only its redacted report. Keep transaction, quote, metadata, and raw
response files private; do not run qualification or valuation until the result
is reviewed.
