# Phase 7 Package 40 - Bounded OpenFIGI Metadata Bootstrap

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ 8b5b5b84eda15b8e723462ee756abd6ee6ed61ea`.

## Result

Added a bounded OpenFIGI v3 adapter, bootstrap service, and CLI. The service
reconstructs ISIN-keyed open positions, requires exact private quote coverage,
submits deterministic `ID_ISIN` batches, and accepts only one unique provider
ticker equal to the candidate quote ticker. Provider warnings/errors, missing
FIGIs, malformed or misaligned JSON, alternate tickers, network failure, and
archive collisions fail closed.

Every successful HTTP response is preserved as exact private bytes using
exclusive creation and file synchronization before parsing. Per-instrument
metadata records the sorted matching FIGI identities and response SHA-256,
leaves `exchange_code` null, and is atomically published through the existing
schema-version-1 document. Duplicate rows with the same confirmed ticker remain
traceable; conflicting tickers are never resolved by first-row selection.

The schema-version-1 operational report contains only requested, matched,
batch, and archived-response counts. Failures after one or more responses were
archived preserve the archived count. Paths, ISINs, tickers, FIGIs, raw bodies,
and credentials are excluded. An optional `OPENFIGI_API_KEY` changes batching
from five to 100 jobs; the key is never accepted on the command line.

This package uses synthetic clients only. It does not transmit private ISINs,
run quote qualification, mutate transactions, create valuation, or execute the
integrated workflow.

## Verification

```text
initial focused: no tests collected (incorrect nonexistent test path)
focused rerun: 48 passed
full: 2808 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```

## Next step

After push, run one controlled private OpenFIGI bootstrap and return only its
redacted report. Keep transaction SQLite, quote JSON, metadata JSON, exact raw
responses, and any API key private. Do not run quote qualification or valuation
until the bootstrap result is reviewed.
