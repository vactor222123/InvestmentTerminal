import pytest

from investment_terminal.persistence.sqlite_inventory import (
    GROUNDED_GENERATION_SQLITE,
    HISTORY_SQLITE,
    KNOWLEDGE_SQLITE,
    PROVIDER_USAGE_COST_SQLITE,
    SQLiteAuthorityClass,
    SQLiteBackupRequirement,
    require_sqlite_persistence_boundary,
    sqlite_persistence_inventory,
)


def test_inventory_is_complete_and_identity_unique() -> None:
    inventory = sqlite_persistence_inventory()

    assert inventory == (
        HISTORY_SQLITE,
        KNOWLEDGE_SQLITE,
        PROVIDER_USAGE_COST_SQLITE,
        GROUNDED_GENERATION_SQLITE,
    )
    assert len(
        {boundary.identity for boundary in inventory}
    ) == 4


def test_history_sqlite_is_rebuildable_projection() -> None:
    assert (
        HISTORY_SQLITE.authority_class
        == SQLiteAuthorityClass.REBUILDABLE_PROJECTION
    )
    assert (
        HISTORY_SQLITE.backup_requirement
        == SQLiteBackupRequirement.REBUILD_FROM_UPSTREAM_AUTHORITY
    )
    assert not HISTORY_SQLITE.runtime_managed


def test_knowledge_sqlite_is_rebuildable_with_availability_backup() -> None:
    assert (
        KNOWLEDGE_SQLITE.authority_class
        == SQLiteAuthorityClass.REBUILDABLE_DERIVED_STATE
    )
    assert (
        KNOWLEDGE_SQLITE.backup_requirement
        == SQLiteBackupRequirement.BACKUP_FOR_AVAILABILITY
    )
    assert KNOWLEDGE_SQLITE.runtime_managed


def test_provider_ledger_is_durable_operational_record() -> None:
    assert (
        PROVIDER_USAGE_COST_SQLITE.authority_class
        == SQLiteAuthorityClass.DURABLE_OPERATIONAL_RECORD
    )
    assert (
        PROVIDER_USAGE_COST_SQLITE.backup_requirement
        == SQLiteBackupRequirement.BACKUP_REQUIRED_FOR_DURABLE_RECORD
    )


def test_grounded_generations_are_durable_generated_evidence() -> None:
    assert (
        GROUNDED_GENERATION_SQLITE.authority_class
        == SQLiteAuthorityClass.DURABLE_GENERATED_EVIDENCE
    )
    assert (
        GROUNDED_GENERATION_SQLITE.backup_requirement
        == SQLiteBackupRequirement.BACKUP_REQUIRED_FOR_DURABLE_RECORD
    )


def test_all_boundaries_are_versioned_wal_and_restore_validated() -> None:
    for boundary in sqlite_persistence_inventory():
        assert boundary.schema_versioned
        assert boundary.uses_wal
        assert boundary.restore_requires_validation


def test_require_boundary_fails_closed() -> None:
    assert (
        require_sqlite_persistence_boundary(
            "KNOWLEDGE_SQLITE@1"
        )
        is KNOWLEDGE_SQLITE
    )

    with pytest.raises(KeyError):
        require_sqlite_persistence_boundary(
            "UNKNOWN@1"
        )

    with pytest.raises(ValueError):
        require_sqlite_persistence_boundary(
            ""
        )
