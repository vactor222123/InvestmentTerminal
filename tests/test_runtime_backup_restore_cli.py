from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)
from investment_terminal.cli.runtime_backup_restore import main
from investment_terminal.knowledge.sqlite_store import KnowledgeSQLiteStore
from investment_terminal.persistence.runtime_backup_service import (
    RuntimeSQLiteBackupService,
    RuntimeSQLiteBackupSources,
)


NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


def make_runtime(root: Path) -> tuple[Path, Path, Path]:
    knowledge = root / "knowledge.db"
    ledger = root / "provider_usage_cost.db"
    generations = root / "grounded_generations.db"
    KnowledgeSQLiteStore(knowledge).initialize()
    GroundedProviderUsageCostLedgerSQLiteStore(ledger).initialize()
    GroundedGenerationSQLiteStore(generations).initialize()
    return knowledge, ledger, generations


def test_validate_command_reports_valid_backup_set(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    knowledge, ledger, generations = make_runtime(tmp_path / "live")
    backup = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=RuntimeSQLiteBackupSources(
            knowledge_database=knowledge,
            usage_cost_ledger_database=ledger,
            grounded_generation_database=generations,
        ),
        clock=lambda: NOW,
    ).create_backup_set()

    main(["validate", "--backup-set", str(backup.directory)])

    output = capsys.readouterr().out
    assert "Runtime SQLite Restore Validation" in output
    assert backup.backup_set_id in output


def test_restore_requires_explicit_offline_confirmation(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "restore",
                "--backup-set",
                str(tmp_path / "backup"),
                "--knowledge-database",
                str(tmp_path / "knowledge.db"),
                "--usage-cost-ledger-database",
                str(tmp_path / "ledger.db"),
                "--grounded-generation-database",
                str(tmp_path / "generations.db"),
            ]
        )

    assert exc.value.code == 2
