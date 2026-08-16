# Runtime Backup / Restore CLI

Sprint 32 Task 6 adds a thin operator CLI and a dedicated restore-activation
service.

## Commands

```text
python -m investment_terminal.cli.runtime_backup_restore backup ...
python -m investment_terminal.cli.runtime_backup_restore validate ...
python -m investment_terminal.cli.runtime_backup_restore restore ...
```

`--json` follows the existing CLI convention for machine-readable output.

## Boundary

The CLI owns only:

```text
argument parsing
→ explicit operator intent
→ service orchestration
→ human/JSON output
```

It does not own SQLite backup, schema validation, WAL handling, atomic
replacement, or rollback mechanics.

## Restore Activation

Actual activation lives in:

```text
investment_terminal/persistence/runtime_restore_activation.py
```

Restore is an **offline operator workflow**. The CLI requires:

```text
--confirm-offline
```

This is an explicit acknowledgement that the production runtime is stopped and
no process is using the target SQLite databases.

## Activation Algorithm

```text
validate backup set
→ create WAL-safe rollback snapshots of existing live DBs
→ stage validated candidate DBs
→ checkpoint live WAL and switch target journal_mode to DELETE
→ close SQLite connection
→ remove stale target WAL/SHM sidecars
→ replace live DBs one by one
→ sync destination directories
```

If replacement fails after earlier targets were changed:

```text
rollback previously replaced DBs from WAL-safe rollback snapshots
→ surface failure
```

This does not claim a cross-filesystem atomic transaction. It provides
compensating rollback for the three-file runtime set.

## Safety

- History SQLite is not exposed by this CLI.
- backup artifacts may not also be restore targets.
- runtime restore targets must be distinct file-backed SQLite paths.
- restore validation always runs before activation.
- the CLI never silently assumes that the runtime is offline.

## Windows WAL Handle Contract

On Windows, deleting `database.db-wal` while SQLite still owns the sidecar can
fail with `WinError 32`.

Before replacement, the offline restore service therefore opens each existing
live target, runs `PRAGMA wal_checkpoint(TRUNCATE)`, switches
`PRAGMA journal_mode = DELETE`, and closes that connection before deleting any
remaining `-wal`/`-shm` sidecars.

If the target is still busy and cannot be drained out of WAL mode, restore fails
closed rather than forcing replacement.
