from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.ai.generation_repository import (
    InMemoryGroundedGenerationRepository,
)
from investment_terminal.application.grounded_generation_history import (
    GroundedGenerationHistoryService,
)
from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)
from investment_terminal.server.grounded_generation_routes import (
    install_grounded_generation_routes,
)


def record(
    request_id: str,
    minute: int,
) -> PersistedGroundedGeneration:
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
            "answer": {
                "claims": [],
            },
        },
        trace={
            "request_id": request_id,
            "validation_status": "ADMISSIBLE",
        },
    )


def client() -> TestClient:
    repository = InMemoryGroundedGenerationRepository()
    repository.add(record("request-1", 0))
    repository.add(record("request-2", 1))
    repository.add(record("request-3", 2))

    app = FastAPI()
    install_grounded_generation_routes(
        app=app,
        history_service=GroundedGenerationHistoryService(
            repository=repository
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret"
        ),
    )
    return TestClient(app)


def headers() -> dict[str, str]:
    return {
        "X-API-Key": "server-secret",
    }


def test_recent_requires_authentication() -> None:
    response = client().get(
        "/v1/grounded-generations",
        params={"limit": 2},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "SERVER_AUTHENTICATION_REQUIRED"
    )


def test_recent_is_bounded_and_newest_first() -> None:
    response = client().get(
        "/v1/grounded-generations",
        params={"limit": 2},
        headers=headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["count"] == 2
    assert [
        item["request_id"]
        for item in payload["data"]["records"]
    ] == [
        "request-3",
        "request-2",
    ]


def test_recent_limit_is_http_bounded() -> None:
    response = client().get(
        "/v1/grounded-generations",
        params={"limit": 101},
        headers=headers(),
    )

    assert response.status_code == 422


def test_exact_request_returns_complete_record() -> None:
    response = client().get(
        "/v1/grounded-generations/request-2",
        headers=headers(),
    )

    assert response.status_code == 200
    record_data = response.json()["data"]["record"]
    assert record_data["request_id"] == "request-2"
    assert record_data["trace"]["validation_status"] == (
        "ADMISSIBLE"
    )


def test_missing_request_is_404_without_authority_escalation() -> None:
    response = client().get(
        "/v1/grounded-generations/missing",
        headers=headers(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == (
        "GROUNDED_GENERATION_NOT_FOUND"
    )
