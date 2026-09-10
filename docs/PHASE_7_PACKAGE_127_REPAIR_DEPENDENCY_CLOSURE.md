# Phase 7 Package 127 - Repair Dependency Closure

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`4387c248d352aacee2f8d1125475bef90c241d08`.

## Scope

This package implements the dependency decision audited in Package 126. It
does not change Yahoo client code, the default `repair=False` production path,
candle projection, JSON schemas, checkpoints, SQLite, ingestion, batch 20, or
the manifest drain. It makes no provider request and reads no private runtime
input.

## Implementation

The runtime source and legacy combined manifest now declare the supported
provider capability:

```text
yfinance[repair]>=0.2.65
```

Both Python 3.13 hash locks were regenerated with the exact-pinned compiler.
The existing `yfinance==1.6.0` pin and all unrelated pins remain unchanged.
The runtime and development locks now contain:

```text
cloudpickle==3.1.2
joblib==1.6.0
narwhals==2.26.0
scikit-learn==1.9.1
scipy==1.18.1
threadpoolctl==3.6.0
yfinance[repair]==1.6.0
```

SciPy and scikit-learn remain transitive dependencies owned by yfinance's
official `repair` extra rather than independent InvestmentTerminal direct
requirements.

Dependency-contract tests fail if either source manifest loses the extra or if
either generated lock loses yfinance, SciPy, or scikit-learn. Existing direct-
dependency parity continues to normalize extras to the distribution name.

## Verification

Independent clean Python 3.13 runtime and development virtual environments
both installed successfully with `--require-hashes`. Each environment passed
`pip check` and imported `scipy.ndimage`, `sklearn.cluster.DBSCAN`, and
`yfinance 1.6.0`.

Focused dependency, repaired-client, and architecture checks passed:
`27 passed`. The complete suite passed with `3033 passed, 4 skipped, 1 warning`;
the warning is the existing Starlette `httpx` deprecation warning.
`git diff --check` is clean.

## Gate

Run exactly one controlled schema-version-2 repaired-series qualification
against the unchanged private manifest and batch-19 checkpoint. Return only
the redacted report for review. Do not persist repaired candles, retry batch 19
ingestion, execute batch 20, or resume the broader drain until that result is
reviewed.
