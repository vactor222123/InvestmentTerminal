from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.cli.knowledge import main
from investment_terminal.knowledge.projection import (
    HistoricalSnapshotKnowledgeProjectionService,
    HistoricalSnapshotKnowledgeSource,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


def dt(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 8, day, hour, 0, tzinfo=timezone.utc)


def source(snapshot_id: str, day: int, checksum_char: str):
    return HistoricalSnapshotKnowledgeSource(
        snapshot_id=snapshot_id,
        package_id=f"review-{day:03d}",
        generated_at=dt(day),
        archived_at=dt(day, 13),
        checksum_sha256=checksum_char * 64,
    )


def seed(database: Path) -> None:
    repo = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(database)
    )
    projector = HistoricalSnapshotKnowledgeProjectionService()

    first = projector.project(
        source(
            "11111111-1111-4111-8111-111111111111",
            1,
            "a",
        ),
        subject_key="WORLD",
        generated_at=dt(2),
        version=1,
    )
    # Same knowledge_id, second version, different source evidence and statement
    # are created explicitly so temporal comparison exercises real persisted data.
    second_projected = projector.project(
        source(
            "22222222-2222-4222-8222-222222222222",
            3,
            "b",
        ),
        subject_key="WORLD",
        generated_at=dt(4),
        version=2,
    )

    from investment_terminal.knowledge.models import KnowledgeRecord

    second = KnowledgeRecord(
        knowledge_id=first.knowledge_id,
        knowledge_type=second_projected.knowledge_type,
        version=2,
        subject_key=second_projected.subject_key,
        statement=second_projected.statement,
        valid_from=second_projected.valid_from,
        valid_to=second_projected.valid_to,
        generated_at=second_projected.generated_at,
        evidence=second_projected.evidence,
        status=second_projected.status,
    )

    repo.add(first)
    repo.add(second)


def test_real_sqlite_to_cli_json_e2e(tmp_path: Path, capsys) -> None:
    database = tmp_path / "knowledge.db"
    seed(database)

    main([
        "--database",
        str(database),
        "--json",
        "compare",
        "--knowledge-id",
        "HISTORICAL_SNAPSHOT_FACT:11111111-1111-4111-8111-111111111111",
        "--first-version",
        "1",
        "--second-version",
        "2",
    ])

    payload = json.loads(capsys.readouterr().out)

    assert payload["command"] == "compare"
    assert payload["first"]["provenance"]["status"] == "COMPLETE"
    assert payload["second"]["provenance"]["status"] == "COMPLETE"
    assert payload["comparison"]["earlier_identity"].endswith("@1")
    assert payload["comparison"]["later_identity"].endswith("@2")
    assert payload["comparison"]["statement_changed"] is True
    assert payload["comparison"]["evidence_changed"] is True


def test_real_sqlite_to_human_cli_e2e(tmp_path: Path, capsys) -> None:
    database = tmp_path / "knowledge.db"
    seed(database)

    main([
        "--database",
        str(database),
        "latest",
        "--subject",
        "WORLD",
    ])

    output = capsys.readouterr().out

    assert "Knowledge" in output
    assert "subject=WORLD" in output
    assert "provenance=COMPLETE" in output
    assert "@2" in output


def test_knowledge_database_remains_separate_from_history(tmp_path: Path) -> None:
    database = tmp_path / "knowledge.db"
    seed(database)

    assert database.exists()
    assert not (tmp_path / "history.db").exists()
