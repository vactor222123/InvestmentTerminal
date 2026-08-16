# Container Baseline

Sprint 32 Task 9 provides the minimal production container image that consumes
the deployment contract established in Task 32.8.

## Build

```text
docker build -t investment-terminal:local .
```

The image uses the Python 3.13 runtime family and installs only the committed
runtime lock:

```text
python -m pip install --no-cache-dir --require-hashes -r requirements.lock
```

Development/test dependencies are not installed into the production image.

## Runtime User

The server runs as:

```text
investment-terminal:investment-terminal
```

It does not run as root.

## Application Boundary

Application code lives at:

```text
/application
```

The image makes this tree read-only at the filesystem-permission level.

Python bytecode generation is disabled:

```text
PYTHONDONTWRITEBYTECODE=1
```

so normal server execution does not require write access to application code.

## Persistent Boundaries

The image declares:

```text
/runtime
/backups
```

as volume boundaries.

They correspond to the Task 32.8 contract:

```text
/runtime   live runtime SQLite state
/backups   independent backup-set destination
```

The default runtime environment points to:

```text
/runtime/knowledge.db
/runtime/operational/provider_usage_cost.db
/runtime/operational/grounded_generations.db
```

`/runtime` and `/backups` are writable by the non-root runtime user.

`/config` and `/secrets` exist as deployment mount points but are not declared as
writable volumes and are not read automatically by the application.

## Knowledge Prerequisite

The image does not bake a Knowledge database into the image.

A deployment must provide the required Knowledge state beneath `/runtime` (or
explicitly override the legacy-compatible runtime paths).

This preserves the existing authority rule: server startup may initialize
operational SQLite stores, but it does not synthesize Knowledge.

## Secrets

No real secret is copied into the image.

The current application contract continues to receive provider/server secrets
through environment variables injected by the deployment layer.

The Docker build context excludes `.env` files and local SQLite/runtime data.

## Server Command

The canonical container command is:

```text
python -m investment_terminal.cli.server \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1
```

One worker remains mandatory because inbound rate limiting is still
process-local.

## Healthcheck

Container liveness checks:

```text
GET /health
```

using Python's standard library.

The healthcheck intentionally does **not** call `/ready`.

Reason:

```text
/health  → process/application liveness
/ready   → dependency/readiness assessment
```

A temporarily missing provider credential or Knowledge prerequisite should make
the service not-ready; it should not by itself cause the container runtime to
treat the process as dead and continuously restart it.

Readiness remains an orchestrator/deployment concern for the later operational
smoke/security tasks.

## Build Context

`.dockerignore` excludes:

```text
.git / local virtualenvs
tests and development-only lock files
.env secret files
local data/backups
SQLite DB/WAL/SHM files
documentation and development scripts
```

The image receives only the runtime dependency lock and application package
needed by the Dockerfile.

## Non-Goals

Task 32.9 does not add:

- Docker Compose or Kubernetes manifests;
- TLS termination;
- reverse proxy;
- secret-file loading;
- container smoke testing in CI;
- backup scheduling;
- multi-worker shared rate limiting.

Deployment security ownership is Task 32.10.
CI image build/start/readiness verification is Task 32.11.
