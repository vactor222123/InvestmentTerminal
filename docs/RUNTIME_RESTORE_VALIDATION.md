# Runtime SQLite Restore Validation

## Status

Sprint 32 Task 5 introduces fail-closed validation of a runtime SQLite backup set
before any restore activation is allowed.

Canonical implementation:

```text
investment_terminal/persistence/runtime_restore_validation.py
```

## Core Safety Rule

Validation never receives live destination paths and never replaces or
initializes a live database.

```text
backup set
→ metadata validation
→ membership validation
→ artifact validation
→ SQLite integrity validation
→ schema/version validation
→ validated candidate
```

Only a validated candidate may be considered by later restore activation.

## Read-Only SQLite Validation

Candidate databases are opened using a read-only immutable SQLite URI:

```text
mode=ro&immutable=1
```

The validator deliberately does not call the domain stores' `initialize()` or
ordinary `connect()` methods.

That prevents validation from:

- creating missing schema;
- modifying schema metadata;
- enabling WAL on the candidate;
- creating `-wal` or `-shm` sidecars;
- making an invalid backup appear valid through initialization.

## Backup-Set Contract

The validator requires:

```text
schema_version == 1
identity == RUNTIME_SQLITE_BACKUP_SET@1
directory name == backup_set_id
timezone-aware created_at
exactly three runtime database entries
```

Expected runtime boundaries are exactly:

```text
KNOWLEDGE_SQLITE@1
PROVIDER_USAGE_COST_SQLITE@1
GROUNDED_GENERATION_SQLITE@1
```

History, unknown, duplicate, missing, or extra boundary entries fail closed.

## Metadata and Artifact Validation

For each database, validation requires:

```text
owner matches inventory
authority_class matches inventory
backup_requirement matches inventory
backup_file is the exact expected basename
size_bytes matches the actual file
```

The backup directory may contain only:

```text
metadata.json
knowledge.db
provider_usage_cost.db
grounded_generations.db
```

Unexpected artifacts fail closed.

This metadata format does not contain cryptographic hashes, so Task 32.5 does
not claim cryptographic tamper detection. It detects the mismatches that the
existing metadata contract can verify, including size, filename, membership,
classification, SQLite integrity, and schema identity.

## SQLite and Schema Validation

Every candidate database must pass:

```text
PRAGMA quick_check == ok
```

and then match the expected runtime schema identity/version.

Knowledge:

```text
knowledge_schema_metadata
schema_version == KnowledgeSQLiteStore.SCHEMA_VERSION
required Knowledge tables present
```

Provider usage/cost:

```text
provider_usage_cost_schema_metadata
schema_version == GroundedProviderUsageCostLedgerSQLiteStore.SCHEMA_VERSION
required ledger tables present
```

Grounded generations:

```text
grounded_generation_schema_metadata
schema_version == GroundedGenerationSQLiteStore.SCHEMA_VERSION
required generation tables present
```

This prevents a valid SQLite file from being restored into the wrong runtime
boundary.

## Non-Goals

Task 32.5 does not implement:

- live database replacement;
- restore staging/publication;
- backup retention;
- CLI commands;
- scheduled recovery;
- cryptographic backup signing/hashing.

Restore activation and operator orchestration remain later work.
