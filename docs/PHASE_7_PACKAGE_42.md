# Phase 7 Package 42 - Privacy-Safe OpenFIGI Failure Categories

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ baec0444990ee59650d160b7bbff649ab92c968b`.

## Result

The OpenFIGI operational report advances to schema version 2 and adds one
bounded `failure.category` value. Stable categories distinguish input/runtime,
provider request, response archive, response shape, provider error, provider
warning, ticker mismatch or ambiguity, missing FIGI, metadata write, and
unexpected failures. Successful reports still contain `failure: null`.

The bootstrap service assigns categories at the owning boundary and carries
only the enum through `OpenFigiBootstrapFailure`. The report continues to omit
exception messages, provider response text, paths, credentials, ISINs, tickers,
and FIGIs. Existing exact-byte private archives, atomic metadata publication,
batching, fail-closed behavior, and aggregate coverage fields are unchanged.

## Scope

This package uses synthetic clients only. It does not inspect private archives,
transmit private identifiers, rerun the operational bootstrap, qualify quotes,
write valuation evidence, or execute trades.

## Verification

```text
focused OpenFIGI/metadata/architecture checks: 42 passed
full: 2811 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```

## Next step

After push, run one new controlled private OpenFIGI bootstrap with a unique run
identifier and return only its schema-version-2 redacted report. Do not send
private inputs, metadata, or exact response archives; do not qualify quotes or
value the portfolio before reviewing the categorized result.
