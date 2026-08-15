from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.ai.generation_persistence_models import PersistedGroundedGeneration
from investment_terminal.ai.generation_repository import InMemoryGroundedGenerationRepository
from investment_terminal.ai.generation_sqlite_repository import SQLiteGroundedGenerationRepository
from investment_terminal.ai.generation_sqlite_store import GroundedGenerationSQLiteStore


def at(minute: int) -> datetime:
    return datetime(2026, 8, 15, 12, minute, tzinfo=timezone.utc)


def record(request_id: str, *, minute: int) -> PersistedGroundedGeneration:
    return PersistedGroundedGeneration(
        request_id=request_id,
        generated_at=at(minute),
        prompt_protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        answer_protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        provider_identity="STATIC_TEST",
        model_identity="STATIC_MODEL@1",
        selected_knowledge_identities=("WORLD_A@1",),
        cited_knowledge_identities=("WORLD_A@1",),
        generation={"prompt": {"request_id": request_id}, "answer": {"claims": []}},
        trace={"request_id": request_id, "validation_status": "ADMISSIBLE"},
    )


def populate(repository) -> None:
    for item in (
        record("request-b", minute=2),
        record("request-z", minute=0),
        record("request-a", minute=2),
        record("request-m", minute=1),
    ):
        repository.add(item)


def repository_for(*, sqlite: bool, tmp_path: Path):
    if sqlite:
        return SQLiteGroundedGenerationRepository(
            GroundedGenerationSQLiteStore(tmp_path / "grounded_generations.db")
        )
    return InMemoryGroundedGenerationRepository()


@pytest.mark.parametrize("sqlite", [False, True])
def test_recent_is_bounded_and_newest_first(tmp_path: Path, sqlite: bool) -> None:
    repository = repository_for(sqlite=sqlite, tmp_path=tmp_path)
    populate(repository)
    assert [item.request_id for item in repository.list_recent(3)] == [
        "request-b", "request-a", "request-m"
    ]


@pytest.mark.parametrize("sqlite", [False, True])
def test_between_uses_half_open_window_and_deterministic_order(
    tmp_path: Path,
    sqlite: bool,
) -> None:
    repository = repository_for(sqlite=sqlite, tmp_path=tmp_path)
    populate(repository)
    assert [item.request_id for item in repository.list_between(at(1), at(3))] == [
        "request-m", "request-a", "request-b"
    ]


@pytest.mark.parametrize("sqlite", [False, True])
@pytest.mark.parametrize("limit", [0, -1, True])
def test_recent_rejects_invalid_limit(tmp_path: Path, sqlite: bool, limit) -> None:
    repository = repository_for(sqlite=sqlite, tmp_path=tmp_path)
    with pytest.raises(ValueError, match="positive integer"):
        repository.list_recent(limit)


@pytest.mark.parametrize("sqlite", [False, True])
def test_between_requires_timezone_aware_boundaries(
    tmp_path: Path,
    sqlite: bool,
) -> None:
    repository = repository_for(sqlite=sqlite, tmp_path=tmp_path)
    with pytest.raises(ValueError, match="timezone-aware"):
        repository.list_between(datetime(2026, 8, 15, 12, 0), at(3))


@pytest.mark.parametrize("sqlite", [False, True])
def test_between_requires_positive_window(tmp_path: Path, sqlite: bool) -> None:
    repository = repository_for(sqlite=sqlite, tmp_path=tmp_path)
    with pytest.raises(ValueError, match="later than"):
        repository.list_between(at(2), at(2))


def test_sqlite_bounded_queries_survive_reopen(tmp_path: Path) -> None:
    database = tmp_path / "grounded_generations.db"
    repository = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(database)
    )
    populate(repository)
    reopened = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(database)
    )
    assert [item.request_id for item in reopened.list_recent(2)] == [
        "request-b", "request-a"
    ]
    assert [item.request_id for item in reopened.list_between(at(0), at(2))] == [
        "request-z", "request-m"
    ]
