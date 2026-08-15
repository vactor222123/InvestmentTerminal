from datetime import datetime, timezone

import pytest

from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.ai.generation_sqlite_repository import (
    SQLiteGroundedGenerationRepository,
)
from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)


def record(
    request_id: str,
    minute: int,
    *,
    answer_text: str | None = None,
) -> PersistedGroundedGeneration:
    answer = {
        "claims": [],
    }
    if answer_text is not None:
        answer["text"] = answer_text

    return PersistedGroundedGeneration(
        request_id=request_id,
        generated_at=datetime(
            2026,
            8,
            15,
            12,
            minute,
            tzinfo=timezone.utc,
        ),
        prompt_protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        answer_protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        provider_identity="STATIC_TEST",
        model_identity="STATIC_MODEL@1",
        selected_knowledge_identities=("WORLD_A@1",),
        cited_knowledge_identities=("WORLD_A@1",),
        generation={
            "prompt": {
                "request_id": request_id,
            },
            "answer": answer,
        },
        trace={
            "request_id": request_id,
            "validation_status": "ADMISSIBLE",
        },
    )


def test_store_initializes_schema_version(
    tmp_path,
) -> None:
    store = GroundedGenerationSQLiteStore(
        tmp_path / "grounded_generations.db"
    )
    store.initialize()

    assert store.schema_version() == 1


def test_repository_round_trip_survives_reopen(
    tmp_path,
) -> None:
    database = tmp_path / "grounded_generations.db"
    repository = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(database)
    )
    expected = record("request-001", 1)

    repository.add(expected)

    reopened = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(database)
    )

    assert reopened.require("request-001") == expected


def test_repository_rejects_duplicate_request_identity(
    tmp_path,
) -> None:
    repository = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(
            tmp_path / "grounded_generations.db"
        )
    )
    expected = record("request-001", 1)
    repository.add(expected)

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        repository.add(expected)


def test_repository_list_all_is_deterministic(
    tmp_path,
) -> None:
    repository = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(
            tmp_path / "grounded_generations.db"
        )
    )
    repository.add(record("request-b", 2))
    repository.add(record("request-a", 2))
    repository.add(record("request-c", 1))

    assert [
        item.request_id
        for item in repository.list_all()
    ] == [
        "request-c",
        "request-a",
        "request-b",
    ]


def test_unicode_generation_round_trips_exactly(
    tmp_path,
) -> None:
    repository = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(
            tmp_path / "grounded_generations.db"
        )
    )
    expected = record(
        "request-001",
        1,
        answer_text="Європа — стабільна.",
    )

    repository.add(expected)

    actual = repository.require(
        "request-001"
    )

    assert actual.to_dict()["generation"] == (
        expected.to_dict()["generation"]
    )
