from datetime import datetime, timezone

import pytest

from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.ai.generation_repository import (
    InMemoryGroundedGenerationRepository,
)


def record(
    request_id: str = "request-001",
    *,
    status: str = "ADMISSIBLE",
) -> PersistedGroundedGeneration:
    return PersistedGroundedGeneration(
        request_id=request_id,
        generated_at=datetime(
            2026, 8, 15, 12, 0, tzinfo=timezone.utc
        ),
        prompt_protocol_identity="GROUNDED_PROMPT@1",
        answer_protocol_identity="GROUNDED_ANSWER@1",
        provider_identity="OPENAI",
        model_identity="gpt-test",
        selected_knowledge_identities=("knowledge-a@1",),
        cited_knowledge_identities=("knowledge-a@1",),
        generation={
            "prompt": {
                "request_id": request_id,
            },
            "answer": {
                "claims": [],
            },
        },
        trace={
            "request_id": request_id,
            "validation_status": status,
        },
    )


def test_model_is_deterministically_serializable() -> None:
    value = record()
    assert value.to_dict()["request_id"] == "request-001"
    assert value.to_dict()["generated_at"] == (
        "2026-08-15T12:00:00+00:00"
    )


def test_rejected_generation_cannot_be_persisted_model() -> None:
    with pytest.raises(
        ValueError,
        match="ADMISSIBLE",
    ):
        record(status="REJECTED")


def test_citations_must_be_selected_context() -> None:
    with pytest.raises(
        ValueError,
        match="subset",
    ):
        PersistedGroundedGeneration(
            request_id="request-001",
            generated_at=datetime(
                2026, 8, 15, 12, 0, tzinfo=timezone.utc
            ),
            prompt_protocol_identity="prompt@1",
            answer_protocol_identity="answer@1",
            provider_identity="OPENAI",
            model_identity="gpt-test",
            selected_knowledge_identities=("knowledge-a@1",),
            cited_knowledge_identities=("knowledge-b@1",),
            generation={
                "prompt": {"request_id": "request-001"},
            },
            trace={
                "request_id": "request-001",
                "validation_status": "ADMISSIBLE",
            },
        )


def test_repository_is_immutable_by_request_identity() -> None:
    repository = InMemoryGroundedGenerationRepository()
    value = record()

    assert repository.add(value) is value
    assert repository.require("request-001") is value

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        repository.add(value)


def test_repository_order_is_deterministic() -> None:
    repository = InMemoryGroundedGenerationRepository()
    repository.add(record("request-b"))
    repository.add(record("request-a"))

    assert [
        item.request_id
        for item in repository.list_all()
    ] == [
        "request-a",
        "request-b",
    ]


def test_require_missing_fails_closed() -> None:
    repository = InMemoryGroundedGenerationRepository()

    with pytest.raises(KeyError):
        repository.require("missing")
