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
    generation: dict | None = None,
    trace: dict | None = None,
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
        generation=(
            generation
            if generation is not None
            else {
                "prompt": {
                    "request_id": request_id,
                    "messages": [
                        {
                            "role": "user",
                            "content": "question",
                        }
                    ],
                },
                "answer": {
                    "claims": [],
                },
            }
        ),
        trace=(
            trace
            if trace is not None
            else {
                "request_id": request_id,
                "validation_status": status,
                "warnings": [],
            }
        ),
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


def test_source_generation_mutation_cannot_change_persisted_evidence() -> None:
    generation = {
        "prompt": {
            "request_id": "request-001",
            "messages": [
                {
                    "role": "user",
                    "content": "original",
                }
            ],
        },
        "answer": {
            "claims": [],
        },
    }
    trace = {
        "request_id": "request-001",
        "validation_status": "ADMISSIBLE",
        "warnings": [],
    }

    value = record(
        generation=generation,
        trace=trace,
    )

    generation["prompt"]["request_id"] = "tampered"
    generation["prompt"]["messages"][0]["content"] = "tampered"
    trace["validation_status"] = "REJECTED"
    trace["warnings"].append("tampered")

    assert value.generation["prompt"]["request_id"] == "request-001"
    assert (
        value.generation["prompt"]["messages"][0]["content"]
        == "original"
    )
    assert value.trace["validation_status"] == "ADMISSIBLE"
    assert value.trace["warnings"] == ()


def test_nested_persisted_evidence_rejects_mutation() -> None:
    value = record()

    with pytest.raises(
        TypeError,
        match="immutable",
    ):
        value.trace["validation_status"] = "REJECTED"

    with pytest.raises(
        TypeError,
        match="immutable",
    ):
        value.generation["prompt"]["request_id"] = "tampered"

    with pytest.raises(TypeError):
        value.generation["prompt"]["messages"][0]["content"] = "tampered"

    with pytest.raises(AttributeError):
        value.trace["warnings"].append("tampered")


def test_to_dict_returns_detached_mutable_projection() -> None:
    value = record()

    first = value.to_dict()
    first["trace"]["validation_status"] = "REJECTED"
    first["trace"]["warnings"].append("tampered")
    first["generation"]["prompt"]["request_id"] = "tampered"
    first["generation"]["prompt"]["messages"][0]["content"] = "tampered"

    second = value.to_dict()

    assert second["trace"]["validation_status"] == "ADMISSIBLE"
    assert second["trace"]["warnings"] == []
    assert second["generation"]["prompt"]["request_id"] == "request-001"
    assert (
        second["generation"]["prompt"]["messages"][0]["content"]
        == "question"
    )


def test_non_json_nested_value_is_rejected() -> None:
    generation = {
        "prompt": {
            "request_id": "request-001",
        },
        "unsupported": {
            "value": object(),
        },
    }

    with pytest.raises(
        TypeError,
        match="JSON-compatible",
    ):
        record(
            generation=generation
        )
