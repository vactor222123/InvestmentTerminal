# Runtime Filesystem Contract

## Status

Sprint 32 introduces an explicit production runtime filesystem contract.

## Compatibility Rule

Existing deployments keep their configured database paths unchanged.

The new environment variable:

```text
INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT
```

is optional.

When it is absent, the established explicit-path behavior remains active.

When it is configured, it becomes a strict ownership/confinement boundary for:

```text
Knowledge database
provider usage/cost database
grounded-generation database
```

The contract does not relocate any database.

## Production Validation

Before operational SQLite stores are initialized, production startup validates:

```text
runtime root is a directory
→ all configured database paths resolve inside the root
→ symlink/junction-like path escape is rejected
→ root is readable
→ operational database parents exist and are writable
→ an existing Knowledge path is a readable file
```

A missing Knowledge database is not created by the filesystem contract.
Readiness remains responsible for reporting the Knowledge database as
`NOT_READY`.

## Why the Contract Is Opt-In

Before Sprint 32, callers could configure arbitrary explicit database paths.
Making a new root mandatory would silently invalidate established deployments
and tests.

Sprint 32 therefore introduces strict confinement without performing a hidden
migration.

A later deployment-layout/container task may make a specific root part of the
deployment profile after migration/volume semantics are explicit.

## Example

```text
INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT=data/knowledge
INVESTMENT_TERMINAL_KNOWLEDGE_DATABASE=data/knowledge/knowledge.db
INVESTMENT_TERMINAL_PROVIDER_USAGE_COST_DATABASE=data/knowledge/provider_usage_cost.db
INVESTMENT_TERMINAL_GROUNDED_GENERATION_DATABASE=data/knowledge/grounded_generations.db
```

## Non-Goals

Task 32.1 does not implement:

- backup or restore;
- database relocation/migration;
- container volumes;
- application lifespan/shutdown;
- distributed storage;
- TLS or secret management.

Those remain later Sprint 32 tasks.
