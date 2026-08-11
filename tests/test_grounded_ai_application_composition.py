from pathlib import Path

import pytest

from investment_terminal.application import composition


def test_composition_rejects_missing_database(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="Knowledge database does not exist",
    ):
        composition.build_live_grounded_ai_application(
            database=tmp_path / "missing.db",
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=0,
            governance_policy=object(),  # type: ignore[arg-type]
        )


def test_composition_owns_query_and_provider_construction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")

    calls = {}

    class FakeStore:
        def __init__(self, path):
            calls["store_path"] = path

    class FakeRepository:
        def __init__(self, store):
            calls["repository_store"] = store

    class FakeQuery:
        def __init__(self, repository):
            calls["query_repository"] = repository

    class FakeGeneration:
        pass

    class FakeApplication:
        def __init__(self, **kwargs):
            calls["application"] = kwargs

    monkeypatch.setattr(
        composition,
        "KnowledgeSQLiteStore",
        FakeStore,
    )
    monkeypatch.setattr(
        composition,
        "SQLiteKnowledgeRecordRepository",
        FakeRepository,
    )
    monkeypatch.setattr(
        composition,
        "KnowledgeQueryService",
        FakeQuery,
    )
    monkeypatch.setattr(
        composition,
        "build_openai_grounded_generation_service",
        lambda **kwargs: (
            calls.setdefault(
                "generation_kwargs",
                kwargs,
            )
            or FakeGeneration()
        ),
    )
    monkeypatch.setattr(
        composition,
        "LiveGroundedAIApplicationService",
        FakeApplication,
    )

    result = (
        composition.build_live_grounded_ai_application(
            database=database,
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=2,
            governance_policy=object(),  # type: ignore[arg-type]
            requested_max_output_tokens=123,
        )
    )

    assert isinstance(
        result,
        FakeApplication,
    )
    assert calls["store_path"] == database
    assert (
        calls["generation_kwargs"][
            "model_identity"
        ]
        == "gpt-test"
    )
    assert (
        calls["generation_kwargs"][
            "max_output_tokens"
        ]
        == 123
    )
    assert "query" in calls["application"]
    assert "generation_service" in calls["application"]
