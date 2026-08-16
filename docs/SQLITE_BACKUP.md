# Consistent SQLite Backup Primitive

## Status

Sprint 32 Task 3 introduces one cross-domain SQLite backup primitive:

```text
investment_terminal/persistence/sqlite_backup.py
```

It does not orchestrate multiple databases and it does not activate restores.

## Policy Boundary

Every backup request identifies one boundary from:

```text
investment_terminal/persistence/sqlite_inventory.py
```

Unknown identities fail closed.

The primitive does not change the authority classification established by
Task 32.2.

## Backup Algorithm

```text
validate inventory identity
→ require existing file-backed SQLite source
→ require separate SQLite destination path
→ create temp DB in destination directory
→ open source read-only
→ SQLite Connection.backup(temp destination)
→ close source + destination SQLite handles
→ PRAGMA quick_check on temp backup
→ close validation handle
→ fsync backup file
→ atomic os.replace publication
→ sync destination directory where supported
→ cleanup temp output on any pre-publication failure
```

This is intentionally not a raw `.db` file copy.

SQLite's backup API produces a consistent snapshot and includes committed state
that may still be represented through WAL.

## Windows Contract

All SQLite connection handles are closed before `os.replace`.

The completed temporary backup is reopened as `r+b` for `os.fsync`. On Windows, `os.fsync` is backed by the CRT `_commit()` operation and requires a descriptor with write access; the zero-content-change reopen provides that access without mutating the backup.

This is a required ordering guarantee because Windows does not permit the same
rename/replace behavior while files remain open that POSIX often permits.

Directory fsync behavior is delegated to the existing repository-owned
`sync_directory()` helper, which already contains the platform policy.

## Destination Policy

Existing backup destinations are protected by default:

```text
overwrite=False
```

Replacement requires explicit:

```text
overwrite=True
```

The primitive never permits source and destination to identify the same file.

## Validation

Task 32.3 performs storage-level validation only:

```text
PRAGMA quick_check == ok
```

Boundary-specific schema/identity validation belongs to restore validation in
Task 32.5.

This separation prevents the generic backup primitive from importing History,
Knowledge, AI, or provider-domain schema internals.

## Failure Semantics

Before publication:

```text
failure
→ no destination publication
→ temporary backup cleanup
```

If `os.replace` fails while an existing destination is being explicitly
replaced, the previous destination remains unchanged and the temporary backup is
cleaned up.

A failure in post-publication directory synchronization is surfaced to the
caller as a durability failure; the already-published backup remains present,
matching the existing atomic-write contract.

## Non-Goals

Task 32.3 does not implement:

- multi-database backup orchestration;
- backup naming/retention policy;
- backup metadata manifests;
- restore validation beyond storage integrity;
- restore activation;
- server scheduling;
- CLI commands.

Those belong to later Sprint 32 tasks.
