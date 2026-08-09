from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.repository import (
    KnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def record(
    knowledge_id: str,
    *,
    version: int = 1,
    subject: str = "WORLD",
    valid_from=None,
    valid_to=None,
    generated_at=None,
) -> KnowledgeRecord:
    vf = dt(1) if valid_from is None else valid_from
    ga = dt(2) if generated_at is None else generated_at
    return KnowledgeRecord(
        knowledge_id=knowledge_id,
        knowledge_type="FACT",
        version=version,
        subject_key=subject,
        statement=f"Statement for {knowledge_id}@{version}.",
        valid_from=vf,
        valid_to=valid_to,
        generated_at=ga,
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id=(
                    "11111111-1111-4111-8111-"
                    f"{version:012d}"
                ),
                observed_at=vf,
                checksum_sha256="a" * 64,
            ),
        ),
    )


def repository(
    tmp_path: Path,
) -> SQLiteKnowledgeRecordRepository:
    return SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            tmp_path / "knowledge.db"
        )
    )


def test_store_owns_separate_knowledge_schema(
    tmp_path: Path,
) -> None:
    store = KnowledgeSQLiteStore(
        tmp_path / "knowledge.db"
    )
    store.initialize()

    assert store.schema_version() == 1
    assert store.table_names() == (
        "knowledge_evidence",
        "knowledge_records",
        "knowledge_schema_metadata",
    )


def test_sqlite_repository_satisfies_contract(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path
    )

    assert isinstance(
        repo,
        KnowledgeRecordRepository,
    )


def test_add_get_round_trip_preserves_evidence_order(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path
    )
    item = KnowledgeRecord(
        knowledge_id="WORLD_CONTEXT",
        knowledge_type="FACT",
        version=1,
        subject_key="WORLD",
        statement="Traceable statement.",
        valid_from=dt(1),
        valid_to=None,
        generated_at=dt(3),
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id="snapshot-1",
                observed_at=dt(1),
                checksum_sha256="a" * 64,
            ),
            KnowledgeEvidenceReference(
                evidence_type="SNAPSHOT_COMPARISON",
                evidence_id="comparison-1",
                observed_at=dt(2),
            ),
        ),
    )

    repo.add(
        item
    )
    loaded = repo.require(
        "WORLD_CONTEXT",
        1,
    )

    assert loaded == item
    assert loaded.evidence == item.evidence


def test_duplicate_identity_is_rejected(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path
    )
    item = record(
        "WORLD_CONTEXT"
    )
    repo.add(
        item
    )

    with pytest.raises(
        ValueError,
        match="identity already exists",
    ):
        repo.add(
            item
        )


def test_list_all_matches_contract_order(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path
    )
    first = record(
        "B",
        generated_at=dt(1),
    )
    second = record(
        "A",
        generated_at=dt(3),
    )
    third = record(
        "B",
        version=2,
        generated_at=dt(3),
    )

    for item in (
        third,
        second,
        first,
    ):
        repo.add(
            item
        )

    assert repo.list_all() == (
        first,
        second,
        third,
    )


def test_subject_validity_queries_match_contract(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path
    )
    bounded = record(
        "BOUNDED",
        valid_from=dt(1),
        valid_to=dt(3),
    )
    open_ended = record(
        "OPEN",
        valid_from=dt(3),
        generated_at=dt(3),
    )
    other = record(
        "OTHER",
        subject="EM",
    )

    for item in (
        bounded,
        open_ended,
        other,
    ):
        repo.add(
            item
        )

    assert repo.find_by_subject(
        "WORLD"
    ) == (
        bounded,
        open_ended,
    )
    assert repo.find_valid_at(
        "WORLD",
        at=dt(3),
    ) == (
        bounded,
        open_ended,
    )


def test_latest_for_subject_matches_contract_tiebreak(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path
    )
    older = record(
        "Z",
        version=1,
        generated_at=dt(2),
    )
    tie_a = record(
        "A",
        version=2,
        generated_at=dt(3),
    )
    tie_z = record(
        "Z",
        version=2,
        generated_at=dt(3),
    )

    for item in (
        tie_a,
        older,
        tie_z,
    ):
        repo.add(
            item
        )

    assert repo.latest_for_subject(
        "WORLD"
    ) == tie_z


def test_failed_evidence_insert_rolls_back_record(
    tmp_path: Path,
) -> None:
    repo = repository(
        tmp_path
    )
    item = record(
        "ROLLBACK"
    )

    original = item.evidence
    object.__setattr__(
        item,
        "evidence",
        (
            original[0],
            original[0],
        ),
    )

    with pytest.raises(
        ValueError,
        match="evidence violates repository constraints",
    ):
        repo.add(
            item
        )

    assert repo.get(
        "ROLLBACK",
        1,
    ) is None


def test_history_schema_is_not_required_or_modified(
    tmp_path: Path,
) -> None:
    knowledge_path = (
        tmp_path / "knowledge.db"
    )
    repo = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            knowledge_path
        )
    )
    repo.add(
        record(
            "WORLD_CONTEXT"
        )
    )

    assert knowledge_path.exists()
    assert not (
        tmp_path / "history.db"
    ).exists()
