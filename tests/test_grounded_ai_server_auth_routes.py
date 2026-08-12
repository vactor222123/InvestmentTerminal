from pathlib import Path

from fastapi.testclient import TestClient

from investment_terminal.api.http_handler import (
    GroundedAIHTTPHandler,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)
from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)
from investment_terminal.server.fastapi_app import (
    create_grounded_ai_fastapi_app,
)


class SuccessService(
    GroundedAIApplicationService
):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={
                "prompt": {
                    "request_id": request.request_id,
                }
            },
            trace={
                "request_id": request.request_id,
            },
        )


def app():
    return create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret",
        ),
    )


def test_grounded_ai_requires_api_key() -> None:
    response = TestClient(
        app()
    ).post(
        "/v1/grounded-ai",
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "SERVER_AUTHENTICATION_REQUIRED"
    )


def test_grounded_ai_rejects_wrong_api_key() -> None:
    response = TestClient(
        app()
    ).post(
        "/v1/grounded-ai",
        headers={
            "X-API-Key": "wrong",
        },
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )

    assert response.status_code == 401


def test_grounded_ai_accepts_valid_api_key() -> None:
    response = TestClient(
        app()
    ).post(
        "/v1/grounded-ai",
        headers={
            "X-API-Key": "server-secret",
        },
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"


def test_health_and_ready_are_not_auth_protected() -> None:
    client = TestClient(
        app()
    )

    assert client.get(
        "/health"
    ).status_code == 200

    assert client.get(
        "/ready"
    ).status_code == 503
