from datetime import datetime, timezone

import pytest

from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.repository import (
    InMemoryKnowledgeRecordRepository,
    KnowledgeRecordRepository,
)


def dt(day: int, hour: int = 12) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
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


def repository() -> InMemoryKnowledgeRecordRepository:
    return InMemoryKnowledgeRecordRepository()


def test_reference_implementation_satisfies_repository_abstraction() -> None:
    repo = repository()

    assert isinstance(
        repo,
        KnowledgeRecordRepository,
    )


def test_add_get_and_require_exact_version() -> None:
    repo = repository()
    item = record(
        "WORLD_CONTEXT",
        version=2,
    )

    assert repo.add(item) is item
    assert repo.get(
        "WORLD_CONTEXT",
        2,
    ) is item
    assert repo.require(
        "WORLD_CONTEXT",
        2,
    ) is item
    assert repo.get(
        "WORLD_CONTEXT",
        1,
    ) is None


def test_duplicate_exact_identity_is_rejected() -> None:
    repo = repository()
    item = record(
        "WORLD_CONTEXT",
    )
    repo.add(item)

    with pytest.raises(
        ValueError,
        match="identity already exists",
    ):
        repo.add(item)


def test_same_knowledge_id_different_versions_are_allowed() -> None:
    repo = repository()

    first = record(
        "WORLD_CONTEXT",
        version=1,
    )
    second = record(
        "WORLD_CONTEXT",
        version=2,
        generated_at=dt(3),
    )

    repo.add(first)
    repo.add(second)

    assert repo.get(
        "WORLD_CONTEXT",
        1,
    ) is first
    assert repo.get(
        "WORLD_CONTEXT",
        2,
    ) is second


def test_list_all_has_deterministic_order() -> None:
    repo = repository()
    third = record(
        "B",
        version=2,
        generated_at=dt(3),
    )
    first = record(
        "B",
        version=1,
        generated_at=dt(1),
    )
    second = record(
        "A",
        version=1,
        generated_at=dt(3),
    )

    for item in (
        third,
        second,
        first,
    ):
        repo.add(item)

    assert repo.list_all() == (
        first,
        second,
        third,
    )


def test_find_by_subject_uses_validity_then_generation_order() -> None:
    repo = repository()
    later_validity = record(
        "LATER",
        valid_from=dt(3),
        generated_at=dt(4),
    )
    earlier_validity = record(
        "EARLIER",
        valid_from=dt(1),
        generated_at=dt(5),
    )
    other = record(
        "OTHER",
        subject="EM",
        valid_from=dt(1),
        generated_at=dt(1),
    )

    for item in (
        later_validity,
        other,
        earlier_validity,
    ):
        repo.add(item)

    assert repo.find_by_subject(
        "WORLD"
    ) == (
        earlier_validity,
        later_validity,
    )


def test_find_valid_at_has_inclusive_boundaries() -> None:
    repo = repository()
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
    repo.add(bounded)
    repo.add(open_ended)

    assert repo.find_valid_at(
        "WORLD",
        at=dt(1),
    ) == (
        bounded,
    )
    assert repo.find_valid_at(
        "WORLD",
        at=dt(3),
    ) == (
        bounded,
        open_ended,
    )


def test_latest_for_subject_uses_generated_identity_version_tiebreak() -> None:
    repo = repository()
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
        repo.add(item)

    assert repo.latest_for_subject(
        "WORLD"
    ) is tie_z


def test_missing_require_raises_key_error() -> None:
    repo = repository()

    with pytest.raises(
        KeyError,
        match="No knowledge record found",
    ):
        repo.require(
            "MISSING",
            1,
        )


def test_naive_valid_at_is_rejected() -> None:
    repo = repository()

    with pytest.raises(
        ValueError,
        match="at must be timezone-aware",
    ):
        repo.find_valid_at(
            "WORLD",
            at=datetime(
                2026,
                8,
                1,
                12,
                0,
            ),
        )


def test_invalid_record_type_is_rejected() -> None:
    repo = repository()

    with pytest.raises(
        TypeError,
        match="record must be",
    ):
        repo.add(
            object()  # type: ignore[arg-type]
        )
