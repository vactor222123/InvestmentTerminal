# SQLite Operational Inventory

## Status

Sprint 32 Task 2 classifies repository-owned SQLite persistence before a generic
backup primitive is implemented.

Executable inventory:

```text
investment_terminal/persistence/sqlite_inventory.py
```

## Shared Storage Mechanics

All four SQLite stores currently use schema metadata, explicit transactions,
foreign keys, WAL journaling, and `synchronous=NORMAL`.

Shared mechanics do not imply shared authority or recovery semantics.

## Inventory

| Identity | Owner | Authority class | Runtime managed | Recovery policy |
|---|---|---|---:|---|
| `HISTORY_SQLITE@1` | History | rebuildable projection | no | rebuild from upstream historical authority |
| `KNOWLEDGE_SQLITE@1` | Knowledge | rebuildable derived state | yes | backup for availability |
| `PROVIDER_USAGE_COST_SQLITE@1` | Provider Operational Accounting | durable operational record | yes | backup required |
| `GROUNDED_GENERATION_SQLITE@1` | Grounded AI Generated Evidence | durable generated evidence | yes | backup required |

## History SQLite

History SQLite is not historical source of truth.

```text
immutable archived Review Package JSON
→ manifest/navigation metadata
→ rebuildable structured History SQLite
```

A backup can be an operational convenience, but it must never replace archived
historical evidence as authority.

## Knowledge SQLite

The Knowledge store defines itself as rebuildable. Production grounded AI still
depends on it for availability, so backup is useful without changing authority.

## Provider Usage/Cost SQLite

The ledger records completed provider usage/cost events. These operational facts
cannot be reconstructed reliably after the original provider call. Preservation
therefore requires backup/restore support.

## Grounded Generation SQLite

Persisted admissible generations are downstream generated evidence. They are not
canonical History or Knowledge, but exact generated output cannot be assumed
reproducible by calling a provider again.

## Runtime Scope

The grounded-AI production runtime manages:

```text
KNOWLEDGE_SQLITE@1
PROVIDER_USAGE_COST_SQLITE@1
GROUNDED_GENERATION_SQLITE@1
```

History SQLite remains outside that production runtime lifecycle.

## Contract for Task 32.3

Task 32.3 may implement a generic SQLite backup primitive, but policy remains
owned by this inventory.

Required properties:

```text
inventory identity
→ file-backed SQLite only
→ SQLite backup API, never naive live-file copy
→ WAL-safe consistent snapshot
→ temporary destination
→ backup validation
→ atomic publication
→ partial-output cleanup on failure
```

Restore activation is not part of Task 32.3.
