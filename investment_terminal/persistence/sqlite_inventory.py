"""Declarative inventory of InvestmentTerminal SQLite persistence boundaries."""

from dataclasses import dataclass
from enum import Enum


class SQLiteAuthorityClass(str, Enum):
    REBUILDABLE_PROJECTION = "REBUILDABLE_PROJECTION"
    REBUILDABLE_DERIVED_STATE = "REBUILDABLE_DERIVED_STATE"
    DURABLE_OPERATIONAL_RECORD = "DURABLE_OPERATIONAL_RECORD"
    DURABLE_GENERATED_EVIDENCE = "DURABLE_GENERATED_EVIDENCE"


class SQLiteBackupRequirement(str, Enum):
    REBUILD_FROM_UPSTREAM_AUTHORITY = "REBUILD_FROM_UPSTREAM_AUTHORITY"
    BACKUP_FOR_AVAILABILITY = "BACKUP_FOR_AVAILABILITY"
    BACKUP_REQUIRED_FOR_DURABLE_RECORD = "BACKUP_REQUIRED_FOR_DURABLE_RECORD"


@dataclass(frozen=True, slots=True)
class SQLitePersistenceBoundary:
    identity: str
    owner: str
    authority_class: SQLiteAuthorityClass
    backup_requirement: SQLiteBackupRequirement
    runtime_managed: bool
    schema_versioned: bool
    uses_wal: bool
    restore_requires_validation: bool
    rationale: str


HISTORY_SQLITE = SQLitePersistenceBoundary(
    identity="HISTORY_SQLITE@1",
    owner="History",
    authority_class=SQLiteAuthorityClass.REBUILDABLE_PROJECTION,
    backup_requirement=SQLiteBackupRequirement.REBUILD_FROM_UPSTREAM_AUTHORITY,
    runtime_managed=False,
    schema_versioned=True,
    uses_wal=True,
    restore_requires_validation=True,
    rationale=(
        "Structured History SQLite is a rebuildable normalized projection; "
        "immutable archived Review Packages remain historical source of truth."
    ),
)

KNOWLEDGE_SQLITE = SQLitePersistenceBoundary(
    identity="KNOWLEDGE_SQLITE@1",
    owner="Knowledge",
    authority_class=SQLiteAuthorityClass.REBUILDABLE_DERIVED_STATE,
    backup_requirement=SQLiteBackupRequirement.BACKUP_FOR_AVAILABILITY,
    runtime_managed=True,
    schema_versioned=True,
    uses_wal=True,
    restore_requires_validation=True,
    rationale=(
        "Knowledge SQLite is explicitly rebuildable derived state, while "
        "backup remains useful for production availability."
    ),
)

PROVIDER_USAGE_COST_SQLITE = SQLitePersistenceBoundary(
    identity="PROVIDER_USAGE_COST_SQLITE@1",
    owner="Provider Operational Accounting",
    authority_class=SQLiteAuthorityClass.DURABLE_OPERATIONAL_RECORD,
    backup_requirement=SQLiteBackupRequirement.BACKUP_REQUIRED_FOR_DURABLE_RECORD,
    runtime_managed=True,
    schema_versioned=True,
    uses_wal=True,
    restore_requires_validation=True,
    rationale=(
        "Completed provider usage/cost records are durable operational facts "
        "and cannot be reconstructed reliably after the original call."
    ),
)

GROUNDED_GENERATION_SQLITE = SQLitePersistenceBoundary(
    identity="GROUNDED_GENERATION_SQLITE@1",
    owner="Grounded AI Generated Evidence",
    authority_class=SQLiteAuthorityClass.DURABLE_GENERATED_EVIDENCE,
    backup_requirement=SQLiteBackupRequirement.BACKUP_REQUIRED_FOR_DURABLE_RECORD,
    runtime_managed=True,
    schema_versioned=True,
    uses_wal=True,
    restore_requires_validation=True,
    rationale=(
        "Persisted admissible generations are downstream generated evidence "
        "and must not be assumed exactly reproducible by re-running a provider."
    ),
)

SQLITE_PERSISTENCE_INVENTORY = (
    HISTORY_SQLITE,
    KNOWLEDGE_SQLITE,
    PROVIDER_USAGE_COST_SQLITE,
    GROUNDED_GENERATION_SQLITE,
)


def sqlite_persistence_inventory() -> tuple[SQLitePersistenceBoundary, ...]:
    return SQLITE_PERSISTENCE_INVENTORY


def require_sqlite_persistence_boundary(
    identity: str,
) -> SQLitePersistenceBoundary:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError(
            "identity must be a non-empty string"
        )

    for boundary in SQLITE_PERSISTENCE_INVENTORY:
        if boundary.identity == identity:
            return boundary

    raise KeyError(
        f"unknown SQLite persistence boundary: {identity}"
    )
