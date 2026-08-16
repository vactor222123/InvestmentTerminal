# Runtime Deployment Layout

Sprint 32 Task 8 defines the production filesystem topology consumed by later
container and deployment work.

It does not build a container and it does not relocate an existing database.

## Canonical Topology

A production deployment has five independent roots:

```text
/application
/runtime
/backups
/config
/secrets
```

Their ownership is deliberately different.

| Root | Runtime access | Persistence | Purpose |
| --- | --- | --- | --- |
| `/application` | read-only | image/release | application code and installed dependencies |
| `/runtime` | read/write | persistent | live runtime SQLite state |
| `/backups` | read/write for operator workflow | persistent, independent | published backup sets |
| `/config` | read-only | deployment-managed | non-secret configuration input |
| `/secrets` | read-only | secret-manager/mount managed | secret material, never runtime data |

The roots must be independent. In particular:

```text
/backups MUST NOT be inside /runtime
/runtime MUST NOT be inside /application
/secrets MUST NOT be inside /runtime or /application
```

This separation prevents a live-data volume failure or replacement from also
destroying the only backup copy, and prevents runtime writes from depending on a
writable application tree.

## Canonical Runtime Data Paths

Inside the runtime data root:

```text
/runtime/knowledge.db
/runtime/operational/provider_usage_cost.db
/runtime/operational/grounded_generations.db
```

Equivalent environment:

```text
INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT=/runtime
INVESTMENT_TERMINAL_KNOWLEDGE_DATABASE=/runtime/knowledge.db
INVESTMENT_TERMINAL_PROVIDER_USAGE_COST_DATABASE=/runtime/operational/provider_usage_cost.db
INVESTMENT_TERMINAL_GROUNDED_GENERATION_DATABASE=/runtime/operational/grounded_generations.db
```

This uses the strict confinement contract already enforced by production
startup.

Knowledge is still an external prerequisite. Startup may prepare the runtime
root and operational database parents, but it does not synthesize Knowledge.

## Backup Layout

The backup root is independent from the live runtime root:

```text
/backups/
  runtime-sqlite-<timestamp>/
    metadata.json
    knowledge.db
    provider_usage_cost.db
    grounded_generations.db
```

The backup/restore CLI continues to receive explicit paths. Task 32.8 does not
silently infer or relocate operator targets.

A production backup command therefore binds the live paths explicitly and writes
the set beneath `/backups`.

Restore remains an offline operator workflow and still requires
`--confirm-offline`.

## Configuration Boundary

`/config` is for non-secret deployment configuration.

Environment variables remain the current server configuration interface. A
deployment system may source those values from a file or platform configuration,
but the application does not parse an implicit `/config` file in Task 32.8.

This avoids adding a second configuration authority.

## Secret Boundary

Secret values remain environment-variable driven by the existing runtime
contract.

`/secrets` defines the deployment ownership boundary for a later container or
orchestrator integration; Task 32.8 does not teach the application to read secret
files automatically.

Therefore:

```text
no API key is written into /runtime
no API key is written into /config examples
no API key is projected by GroundedAIServerDeploymentLayout.runtime_environment()
```

The deployment layer is responsible for exposing the required secret values to
the process environment.

## Persistence and Ephemeral State

Persistent:

```text
/runtime
/backups
```

Deployment-managed/read-only:

```text
/application
/config
/secrets
```

Ephemeral process-local state includes:

```text
inbound rate-limit buckets
Python process memory
temporary restore staging/rollback directories created for one operator action
```

The current process-local rate limiter is one reason the canonical server CLI
still requires exactly one worker.

## Migration Rule

Task 32.8 defines the canonical layout for new production deployment profiles.

It does **not** change backward compatibility in `GroundedAIServerRuntimeConfig`:

```text
INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT remains optional
explicit legacy database paths remain valid
no database is silently moved
```

An existing deployment adopts the canonical layout only through an explicit
operator migration.

## Contract Object

`GroundedAIServerDeploymentLayout` is intentionally descriptive.

It:

```text
validates absolute independent roots
projects canonical runtime SQLite paths
projects non-secret runtime path environment
```

It does not:

```text
create directories
move data
create Knowledge
read secrets
start the server
run backup/restore
```

Filesystem creation and confinement remain owned by the existing runtime
filesystem/lifespan contracts.

## Non-Goals

Task 32.8 does not add:

- Dockerfile or container image;
- Compose/Kubernetes manifests;
- reverse proxy or TLS;
- secret-file loading;
- backup scheduling;
- database migration automation;
- multi-worker shared rate limiting.

Those remain later Sprint 32 tasks.
