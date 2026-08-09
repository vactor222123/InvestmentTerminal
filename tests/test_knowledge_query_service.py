from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.query_service import (
    KnowledgeQueryService,
)
from investment_terminal.knowledge.repository import (
    InMemoryKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


def dt(day: int) -> datetime:
    return datetime(2026, 8, day, 12, 0, tzinfo=timezone.utc)


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
                evidence_id="11111111-1111-4111-8111-" + f"{version:012d}",
                observed_at=vf,
                checksum_sha256="a" * 64,
            ),
        ),
    )


def populate(repo):
    first = record("A", generated_at=dt(1))
    second = record(
        "B",
        generated_at=dt(3),
        valid_from=dt(2),
        valid_to=dt(4),
    )
    third = record(
        "C",
        subject="EM",
        generated_at=dt(2),
    )
    for item in (second, third, first):
        repo.add(item)
    return first, second, third


def test_exact_get_returns_envelope() -> None:
    repo = InMemoryKnowledgeRecordRepository()
    item = record("WORLD_CONTEXT", version=2)
    repo.add(item)

    result = KnowledgeQueryService(repository=repo).get(
        "WORLD_CONTEXT",
        2,
    )

    assert result is not None
    assert result.record is item
    assert result.identity_key == "WORLD_CONTEXT@2"
    assert result.provenance.status == "COMPLETE"


def test_missing_get_returns_none() -> None:
    service = KnowledgeQueryService(
        repository=InMemoryKnowledgeRecordRepository()
    )
    assert service.get("MISSING", 1) is None


def test_require_preserves_repository_key_error() -> None:
    service = KnowledgeQueryService(
        repository=InMemoryKnowledgeRecordRepository()
    )
    with pytest.raises(KeyError, match="No knowledge record found"):
        service.require("MISSING", 1)


def test_list_all_preserves_repository_order() -> None:
    repo = InMemoryKnowledgeRecordRepository()
    first, second, third = populate(repo)

    output = KnowledgeQueryService(repository=repo).list_all()

    assert tuple(item.record for item in output) == (
        first,
        third,
        second,
    )


def test_find_by_subject_returns_envelopes_in_repository_order() -> None:
    repo = InMemoryKnowledgeRecordRepository()
    first, second, _ = populate(repo)

    output = KnowledgeQueryService(
        repository=repo
    ).find_by_subject("WORLD")

    assert tuple(item.record for item in output) == (
        first,
        second,
    )
    assert all(item.provenance.status == "COMPLETE" for item in output)


def test_find_valid_at_preserves_inclusive_validity() -> None:
    repo = InMemoryKnowledgeRecordRepository()
    first, second, _ = populate(repo)

    output = KnowledgeQueryService(
        repository=repo
    ).find_valid_at(
        "WORLD",
        at=dt(4),
    )

    assert tuple(item.record for item in output) == (
        first,
        second,
    )


def test_latest_for_subject_returns_latest_envelope() -> None:
    repo = InMemoryKnowledgeRecordRepository()
    _, second, _ = populate(repo)

    result = KnowledgeQueryService(
        repository=repo
    ).latest_for_subject("WORLD")

    assert result is not None
    assert result.record is second


def test_latest_for_missing_subject_returns_none() -> None:
    service = KnowledgeQueryService(
        repository=InMemoryKnowledgeRecordRepository()
    )
    assert service.latest_for_subject("MISSING") is None


def test_same_query_contract_with_sqlite_repository(
    tmp_path: Path,
) -> None:
    repo = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            tmp_path / "knowledge.db"
        )
    )
    first, second, third = populate(repo)
    service = KnowledgeQueryService(repository=repo)

    assert tuple(item.record for item in service.list_all()) == (
        first,
        third,
        second,
    )
    assert tuple(
        item.record
        for item in service.find_by_subject("WORLD")
    ) == (
        first,
        second,
    )
    assert service.latest_for_subject("WORLD").record == second


def test_service_rejects_non_repository() -> None:
    with pytest.raises(
        TypeError,
        match="repository must be",
    ):
        KnowledgeQueryService(
            repository=object(),  # type: ignore[arg-type]
        )
