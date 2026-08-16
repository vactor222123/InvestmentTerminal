# Runtime SQLite Backup Service

## Status

Sprint 32 Task 4 adds backup-set orchestration above the generic SQLite backup
primitive introduced in Task 32.3.

Canonical implementation:

```text
investment_terminal/persistence/runtime_backup_service.py
```

## Runtime Scope

The service backs up exactly the three runtime-managed SQLite boundaries:

```text
KNOWLEDGE_SQLITE@1
PROVIDER_USAGE_COST_SQLITE@1
GROUNDED_GENERATION_SQLITE@1
```

It intentionally excludes:

```text
HISTORY_SQLITE@1
```

because History SQLite is a rebuildable projection outside the grounded-AI
production runtime lifecycle.

## Backup Root Ownership

The backup service requires an explicit `backup_root`.

It does not infer the backup destination from `runtime_data_root` and it does not
relocate live databases.

This keeps the live-data location and backup-destination location as separate
deployment concerns. Environment/CLI wiring can be added later without changing
the backup-set contract.

## Backup-Set Identity

The set identity is deterministic from an injected timezone-aware clock:

```text
runtime-sqlite-YYYYMMDDTHHMMSS.ffffffZ
```

Example:

```text
runtime-sqlite-20260816T123456.123456Z
```

The service rejects a naive datetime.

## Set Layout

```text
<backup_root>/
  runtime-sqlite-20260816T123456.123456Z/
    metadata.json
    knowledge.db
    provider_usage_cost.db
    grounded_generations.db
```

## All-or-Nothing Publication

Task 32.4 uses set-level staging:

```text
create staging directory
→ back up Knowledge
→ back up provider usage/cost
→ back up grounded generations
→ write deterministic metadata
→ atomically rename staging directory to final set directory
→ sync backup root
```

If any database backup or metadata write fails before publication:

```text
staging directory removed
final backup set absent
```

A partially published backup set is therefore never a valid service result.

Existing final set directories are never overwritten.

## Metadata

`metadata.json` records:

```text
schema_version
identity
backup_set_id
created_at
databases[]
```

Each database entry records:

```text
boundary_identity
owner
authority_class
backup_requirement
source_path
backup_file
size_bytes
```

Metadata preserves the authority classification from the Task 32.2 inventory.
Creating a backup does not promote Knowledge, generated evidence, or operational
accounting into a different authority class.

## Non-Goals

Task 32.4 does not implement:

- History backup orchestration;
- retention/deletion policy;
- scheduled backups;
- restore schema/identity validation;
- restore activation;
- CLI commands;
- server startup/shutdown integration.

Restore validation remains Task 32.5.
