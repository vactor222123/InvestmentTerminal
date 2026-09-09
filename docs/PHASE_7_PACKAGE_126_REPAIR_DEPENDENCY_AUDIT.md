# Phase 7 Package 126 - Repaired Retrieval Dependency Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`314e2ddcc379d247cc18accd91e8f614b198d2bb`.

## Scope

This package inspects the repository dependency contract, installed yfinance
`1.6.0` metadata and source, and official package-index metadata. It does not
install packages, contact Yahoo, open private runtime inputs, change a
checkpoint or SQLite, retry ingestion, execute batch 20, or resume the drain.

## Findings

yfinance `1.6.0` publishes an official `repair` extra. Its installed wheel
metadata declares:

```text
Provides-Extra: repair
Requires-Dist: scipy>=1.6.3; extra == "repair"
Requires-Dist: scikit-learn>=1.0; extra == "repair"
```

The same metadata is published by the official PyPI release endpoint:
`https://pypi.org/pypi/yfinance/1.6.0/json`.

The source path is also explicit. For a non-FX frame with more than one row,
the repair flow reaches `_fix_unit_random_mixups`, which imports
`scipy.ndimage` before testing for sporadic unit errors. When missing or
invalid values require finer-interval reconstruction,
`_reconstruct_intervals_batch` imports `sklearn.cluster.DBSCAN`. These are two
parts of the supported repair capability, not interchangeable alternatives.
The redacted Package 125 report remains intentionally insufficient to name the
single module that raised its measured `ModuleNotFoundError`.

The repository currently declares `yfinance>=0.2.65` without the extra. Its
runtime and development locks therefore contain yfinance `1.6.0` but omit
`scipy`, `scikit-learn`, and the latter package's transitive runtime
dependencies. The existing compiler includes `requirements.in` from
`requirements-dev.in`, generates both locks with hashes under Python 3.13, and
must remain the only lock-generation path.

Official PyPI release pages currently expose CPython 3.13 Windows x86-64 and
manylinux x86-64 wheels for compatible SciPy and scikit-learn releases. This
establishes that the supported Windows operator and Linux CI platforms have a
binary-wheel path; the next package's actual resolver and clean installs must
still validate the exact selected versions and hashes.

## Decision

The smallest coherent implementation is to declare the capability through the
provider's own extra:

```text
yfinance[repair]>=0.2.65
```

Use that form in `requirements.in` and the legacy combined
`requirements.txt`. Do not add independent direct `scipy` or `scikit-learn`
lines: InvestmentTerminal owns yfinance repaired retrieval, while yfinance's
versioned extra owns its repair dependency set. Regenerate
`requirements.lock` and `requirements-dev.lock` with
`scripts/compile_requirements.ps1`; never hand-edit either lock.

The implementation package must add dependency-contract assertions that the
runtime source selects the `repair` extra and both generated locks contain the
resolved SciPy and scikit-learn distributions. It must verify both hash-locked
runtime and development installs in clean Python 3.13 environments, run
`pip check`, import `scipy.ndimage` and `sklearn.cluster.DBSCAN`, then run the
focused and complete repository suites.

No provider-client code, repair default, report schema, candle projection,
checkpoint, persistence, retry, or drain behavior should change. The existing
schema-version-2 `APIError -> ModuleNotFoundError` failure evidence remains the
fail-closed behavior for an unsupported or stale environment. A supported
runtime is one installed from the completed hash lock.

## Gate

After the dependency implementation and clean-install verification are
complete, run exactly one controlled schema-version-2 repaired qualification
against the unchanged private manifest and batch-19 checkpoint. Until then,
do not install ad hoc packages, make another Yahoo request, persist repaired
candles, retry batch 19 ingestion, execute batch 20, or resume the manifest
drain.

Verification completed with `36 passed` focused dependency,
repaired-qualification, and architecture tests. The complete suite passed with
`3031 passed, 4 skipped, 1 warning`; the warning is the existing Starlette
`httpx` deprecation warning. `git diff --check` is clean.
