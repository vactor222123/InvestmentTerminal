# Phase 7 Package 125 - Repaired Qualification Schema-2 Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`d264aa048c69f9ee7d92f9ad133d0ffb6e007ed9`.

Only the explicitly returned redacted report was reviewed. The private
manifest, checkpoint, cache, database, symbol, currency, and candle values were
not read or added to the repository.

## Measured result

The schema-version-2 report is structurally valid and bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 19 of 601, request checksum
`bba88de6404ac7dae91b7a98aa32a6e0ac32f276bd1d332a7f8c0a449e4f4864`,
and the established ten-year half-open window.

Status is `FAILED`, stable category is `UNEXPECTED`, and the bounded causal
chain is:

```text
investment_terminal.utils.exceptions.APIError
-> builtins.ModuleNotFoundError
```

yfinance 1.6.0 repair was requested, but no frame was returned. Repaired-row
count, repaired-row presence, and coverage therefore remain unknown. The report
does not establish a repaired-series rejection or any candle defect. Its SHA-256
is `bf897f78d2d997a5a8e18f83e2eab8e68d4f2f98efd4a0e3d5448172eb15865f`.

## Dependency finding and boundary

The installed yfinance 1.6.0 source contains lazy repair-path imports of
`scipy.ndimage` for unit-mixup repair and `sklearn.cluster.DBSCAN` for price
reconstruction. `pip show` confirms that neither `scipy` nor `scikit-learn` is
installed, and neither name occurs in the repository dependency manifests or
hash locks.

The privacy-safe report deliberately exposes the exception class rather than
the missing module name, so this package does not claim which lazy import raised
the measured exception. Adding one or both heavy optional dependencies requires
a separate reproducibility audit covering the exact repair paths, supported
Python 3.13 wheels, direct-dependency ownership, lock generation, clean install,
and failure behavior.

Do not install an ad hoc package, repeat repaired qualification, persist
repaired candles, retry batch 19 ingestion, execute batch 20, or resume the
manifest drain before that audit and any selected implementation are complete.

Verification completed with `91 passed` focused provider, qualification,
dependency, and architecture tests. The complete suite passed with `3031
passed, 4 skipped, 1 warning`; the warning is the existing Starlette `httpx`
deprecation warning. `git diff --check` is clean.
