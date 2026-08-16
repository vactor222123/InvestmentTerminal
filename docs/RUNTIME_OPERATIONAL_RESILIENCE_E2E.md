# Real Operational Resilience E2E

Sprint 32 Task 12 proves that the repository-owned runtime backup/restore stack
can recover real durable state across all three runtime-managed SQLite
boundaries.

## Scope

The E2E covers:

```text
Knowledge SQLite
Provider usage/cost SQLite
Grounded-generation SQLite
```

It uses the real domain SQLite schemas and transaction boundaries.

No placeholder database bytes are used.

## Recovery Scenario

The test executes:

```text
initialize all three live stores
→ write distinctive pre-backup durable rows
→ read and freeze expected state
→ create RuntimeSQLiteBackupService backup set
→ validate backup set
→ write distinctive post-backup mutations
→ prove live state differs from backup point
→ activate offline restore
→ construct fresh store objects
→ exact readback of pre-backup state
→ prove post-backup mutations disappeared
→ verify schema versions
```

This proves that restore is not accidentally reading untouched live state.

## Windows Compatibility

Windows + PowerShell + Python 3.13 is the primary local regression environment.

The E2E deliberately relies only on repository-owned Python persistence APIs and
`pytest tmp_path`.

It does not use:

```text
shell rm/mv/cp
POSIX permissions
open-file replacement assumptions
Linux-only paths
Bash
```

All store transactions and read connections are closed before restore
activation.

This is important because Windows does not permit the same unlink/replace
behavior for open SQLite/WAL handles that may appear to work on POSIX systems.

The restore activation service remains responsible for its existing Windows-safe
sequence:

```text
WAL checkpoint
→ journal_mode DELETE
→ close SQLite handle
→ remove WAL/SHM sidecars
→ os.replace
```

## Backup Point Semantics

The backup point contains one distinctive row in each durable boundary.

After the backup is published, the live databases receive a second distinctive
mutation.

After restore:

```text
pre-backup rows must exist exactly
post-backup rows must not exist
```

The test compares complete selected durable rows rather than only row counts.

## Restart Proof

After restore, the test discards the original store objects and creates fresh:

```text
KnowledgeSQLiteStore
GroundedProviderUsageCostLedgerSQLiteStore
GroundedGenerationSQLiteStore
```

Exact readback through fresh store connections is the restart/reopen proof.

## What This Does Not Test

Task 32.12 does not add:

- scheduled backups;
- remote/object backup storage;
- Docker-specific restore;
- reverse proxy/TLS;
- registry publishing;
- external provider calls;
- new domain features.

Those are outside the operational-resilience proof required for Sprint 32.
