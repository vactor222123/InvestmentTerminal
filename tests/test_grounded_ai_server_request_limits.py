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
from investment_terminal.server.request_limits import (
    GroundedAIServerRequestLimitPolicy,
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


class NeverCallService(
    GroundedAIApplicationService
):
    def execute(self, request):
        raise AssertionError(
            "application must not execute"
        )


def client(
    *,
    max_body_bytes: int,
    service=None,
) -> TestClient:
    active_service = (
        service
        if service is not None
        else SuccessService()
    )
    app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=active_service,
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret",
        ),
        request_limit_policy=GroundedAIServerRequestLimitPolicy(
            max_body_bytes=max_body_bytes,
        ),
    )
    return TestClient(app)


def headers():
    return {
        "X-API-Key": "server-secret",
    }


def test_oversized_authenticated_request_returns_413_before_application() -> None:
    response = client(
        max_body_bytes=32,
        service=NeverCallService(),
    ).post(
        "/v1/grounded-ai",
        headers=headers(),
        json={
            "request_id": "request-1",
            "query": "x" * 100,
        },
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == (
        "SERVER_REQUEST_BODY_TOO_LARGE"
    )


def test_unauthenticated_oversized_request_preserves_401_precedence() -> None:
    response = client(
        max_body_bytes=16,
        service=NeverCallService(),
    ).post(
        "/v1/grounded-ai",
        json={
            "request_id": "request-1",
            "query": "x" * 100,
        },
    )

    assert response.status_code == 401


def test_valid_authenticated_request_under_limit_reaches_handler() -> None:
    response = client(
        max_body_bytes=1024,
    ).post(
        "/v1/grounded-ai",
        headers=headers(),
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"


def test_invalid_json_under_limit_returns_400() -> None:
    response = client(
        max_body_bytes=1024,
        service=NeverCallService(),
    ).post(
        "/v1/grounded-ai",
        headers={
            **headers(),
            "Content-Type": "application/json",
        },
        content=b"{not-json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == (
        "SERVER_INVALID_JSON"
    )
