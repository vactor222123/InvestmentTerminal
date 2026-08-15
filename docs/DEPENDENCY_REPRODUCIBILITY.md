# Dependency Reproducibility

## Status

Sprint 31 establishes an explicit dependency-resolution contract.

## Python Baseline

The supported lock-generation interpreter family is:

```text
Python 3.13.x
```

`CodingStandards.md` defines Python 3.13+ as the broader source baseline.
`.python-version` intentionally pins the lock-generation family to `3.13`,
rather than one patch release.

Patch releases such as 3.13.7 or later 3.13.x security/bugfix releases are
accepted. We do not require developers to replace an otherwise valid 3.13
interpreter merely to regenerate dependency locks.

## Dependency Layers

Source manifests:

```text
requirements.in
    runtime direct dependencies

requirements-dev.in
    requirements.in + test/code-quality direct dependencies
```

Compiler toolchain:

```text
requirements-compiler.txt
```

The compiler toolchain remains exact-pinned because changing pip or pip-tools can
change resolution or generated lock output.

Generated artifacts:

```text
requirements.lock
requirements-dev.lock
```

Generated lock files are repository artifacts and should be committed once
compiled.

## Lock Generation

On Windows PowerShell from the repository root:

```powershell
.\scripts\compile_requirements.ps1
```

The script fails closed unless the active interpreter belongs to Python 3.13.x.

It then generates hash-locked files using the pinned pip/pip-tools compiler
toolchain.

Do not generate lock files from `pip freeze`. `pip freeze` captures the current
environment, including accidental/transitive packages, rather than resolving
the declared dependency contract.

## Installation

Runtime environment after locks exist:

```powershell
python -m pip install --require-hashes -r requirements.lock
```

Development/test environment:

```powershell
python -m pip install --require-hashes -r requirements-dev.lock
```

## Updating Dependencies

Dependency updates are explicit:

```text
edit requirements.in and/or requirements-dev.in
→ run compile_requirements.ps1 under Python 3.13.x
→ inspect lock diff
→ install from requirements-dev.lock
→ run full pytest
→ commit source manifest + lock diff together
```

Never hand-edit generated lock files.

## Legacy requirements.txt

`requirements.txt` remains temporarily for compatibility with the existing
developer workflow during Sprint 31.

The source manifests must contain the same direct dependency set. An executable
test guards that equivalence.

After generated locks are validated in CI, installation documentation and
automation should prefer `requirements.lock` / `requirements-dev.lock`.
