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

## Dependency Ownership

Runtime direct dependencies are declared in:

```text
requirements.in
```

Development/test-only direct dependencies are declared in:

```text
requirements-dev.in
```

The legacy `requirements.txt` temporarily mirrors the combined direct set.

Important ownership rule:

```text
FastAPI framework        → fastapi
production ASGI server   → uvicorn
TestClient transport     → httpx (development/test)
```

The project intentionally does **not** depend on `fastapi[standard]`.

That convenience extra pulls optional platform-specific server dependencies such
as `uvloop`. A lock generated on Windows can therefore omit Linux-only optional
dependencies while still retaining an extra that asks pip to install them. In
`--require-hashes` mode that produces an invalid cross-platform install
contract.

Directly declaring only the capabilities the project actually owns avoids this
hidden platform-specific dependency surface.

## Compiler Toolchain

```text
requirements-compiler.txt
```

The compiler toolchain is exact-pinned because resolver/tooling changes can
change generated lock output.

## Generated Artifacts

```text
requirements.lock
requirements-dev.lock
```

Both lock files are generated artifacts and are committed.

## Lock Generation

From Windows PowerShell at repository root:

```powershell
.\scripts\compile_requirements.ps1
```

The script requires Python 3.13.x and generates hash-locked requirements.

Do not use `pip freeze`.

## Installation

Runtime:

```powershell
python -m pip install --require-hashes -r requirements.lock
```

Development/test:

```powershell
python -m pip install --require-hashes -r requirements-dev.lock
```

CI uses the development lock with `--require-hashes`.

## Updating Dependencies

```text
edit source manifest
→ regenerate locks
→ inspect lock diff
→ install from requirements-dev.lock
→ run full pytest
→ commit manifests and locks together
```

Never hand-edit generated lock files.
