# Phase 7 Package 121 - Repaired Series Qualification

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`dc953860e44e8a6df81bc908100a9cfb0491259e`.

## Result

The package implements the separate read-only recovery qualification selected
by Package 120. It validates the private manifest, selected request, and exact
checkpoint coverage before choosing the single failed outcome. It then performs
one explicitly repaired daily yfinance request over the existing half-open
window and projects the returned frame through the unchanged strict production
candle policy.

Production `YahooFinanceClient` retrieval remains `repair=False`. The raw
diagnostic remains unchanged. The qualification has no SQLite repository,
importer, checkpoint writer, retry loop, fallback chain, or drain dependency.

## Contract

The schema-version-1 redacted report is identified as
`MANIFEST_REPAIRED_SERIES_QUALIFICATION`. It binds the manifest checksum, batch
index/count, request checksum, and requested window. It records:

- `QUALIFIED`, `REJECTED`, or `FAILED`;
- explicit `YFINANCE_PRICE_REPAIR_V1` and installed yfinance version;
- that repair was requested, repaired-row count, and repaired-row presence;
- aggregate raw and strictly projected row counts;
- a stable projection or provider failure category.

The report excludes symbol, currency, candle values, row identity, paths,
provider text, and exception messages. `QUALIFIED` requires a non-empty strict
projection. Empty and locally invalid frames remain `REJECTED`; provider,
rate-limit, input, and binding errors remain `FAILED` and exit non-zero.

## Tests and operational boundary

Focused tests cover the exact `repair=True` call, repaired-row accounting,
strict no-omission projection, empty and invalid responses, non-daily rejection,
binding validation before provider access, checkpoint immutability, atomic
report output, privacy, and normalized rate-limit failure.

The next action is one user-executed batch-19 qualification against the existing
private manifest and checkpoint. Return only its redacted report. Do not return
the manifest, checkpoint, cache, database, or any private identity. Do not retry
ingestion or execute batch 20 before the report is reviewed.

Verification: 84 focused repaired-client/service/CLI/diagnostic/architecture
tests passed. The complete suite passed with 3,025 tests, four skips, and one
existing Starlette deprecation warning. `git diff --check` is clean.
