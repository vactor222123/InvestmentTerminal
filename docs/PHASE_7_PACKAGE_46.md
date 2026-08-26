# Phase 7 Package 46 - Candidate-Ticker OpenFIGI Row Filtering

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ b7f5cc5906111233581849aa805f71776821e130`.

## Result

OpenFIGI bootstrap now accepts an ISIN mapping when the private candidate
ticker is present, even if the response also contains alternative listing
tickers. Metadata provenance deterministically retains every non-empty FIGI
from candidate-ticker rows only; alternative rows and their FIGIs are ignored.

Candidate absence still reports `CANDIDATE_TICKER_ABSENT`. Candidate rows with
no FIGI still report `FIGI_MISSING`, even when an alternative listing has a
FIGI. Provider errors/warnings, malformed responses, archive failures, and
metadata-write failures remain fail-closed. No first-row selection or provider
exchange-code-to-MIC projection is introduced.

The schema-version-3 redacted report, exact-byte private archive, metadata
schema version 1, aggregate counts, atomic publication, and privacy exclusions
remain unchanged.

## Scope

This package uses synthetic clients only. It does not inspect private runtime
responses, rerun OpenFIGI, qualify quotes, create valuation, or authorize
trading.

## Verification

```text
focused OpenFIGI/metadata/architecture checks: 42 passed
full: 2811 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```

## Next step

After push, run one controlled OpenFIGI bootstrap with a unique run ID and
return only its redacted schema-version-3 report. Keep all transaction, quote,
metadata, and raw response files private; do not qualify or value until the
result is reviewed.
