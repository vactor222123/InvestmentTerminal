# Continuous Integration

## Status

Sprint 31 introduces the first repository-owned CI quality gate.

Canonical workflow:

```text
.github/workflows/ci.yml
```

## Trigger Policy

CI runs on:

```text
push to develop
pull request targeting develop
```

The workflow is read-only with respect to repository contents.

## Environment

CI uses:

```text
ubuntu-latest
Python 3.13
requirements-dev.lock
```

Dependencies are installed with:

```text
python -m pip install --require-hashes -r requirements-dev.lock
```

This makes the CI environment consume the same hash-locked dependency contract
established by Sprint 31 dependency reproducibility work.

## Required Checks

The CI job executes, in order:

```text
dependency reproducibility contract
→ architecture dependency guards
→ full pytest regression suite
→ git diff --check
```

Focused contract tests run before the full suite so architectural or dependency
contract failures are surfaced early and clearly.

## Why Black/Flake8 Are Not Yet Blocking

Black and Flake8 are present in the development dependency set, but the
repository does not yet have an explicit formatter/linter configuration or a
proven clean baseline for the entire existing codebase.

Sprint 31 therefore does not silently convert them into blocking CI gates.
Doing so could create unrelated mass-formatting/style work and obscure the
higher-value correctness/integrity gate.

A future formatting/lint task should first establish:

```text
explicit configuration
→ clean baseline
→ focused remediation
→ only then blocking CI enforcement
```

## Platform Contract

The first CI gate intentionally runs on Linux.

The existing regression suite is expected to be platform-neutral. Windows
remains an important local development environment, but adding a Windows matrix
before the first Linux gate proves stable would multiply operational surface
without improving the initial correctness guarantee.

A future CI expansion may add Windows if a concrete cross-platform regression
risk justifies it.

## Failure Policy

A failing focused contract test, architecture guard, full pytest suite, or
whitespace check fails the CI job.

CI does not call external provider APIs and does not require repository secrets.
