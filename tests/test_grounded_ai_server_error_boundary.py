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
from investment_terminal.server.error_boundary import (
    GroundedAIServerInternalErrorResponse,
)
from investment_terminal.server.fastapi_app import (
    create_grounded_ai_fastapi_app,
)


class ExplodingService(
    GroundedAIApplicationService
):
    def execute(self, request):
        raise BaseException("not caught by application boundary")


class SuccessService(
    GroundedAIApplicationService
):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={"prompt": {"request_id": request.request_id}},
            trace={"request_id": request.request_id},
        )


def authenticator():
    return GroundedAIServerAPIKeyAuthenticator(
        expected_api_key="server-secret",
    )


def headers():
    return {
        "X-API-Key": "server-secret",
    }


def test_internal_error_response_is_stable_and_sanitized() -> None:
    assert GroundedAIServerInternalErrorResponse().to_dict() == {
        "status": "ERROR",
        "error": {
            "category": "INTERNAL_ERROR",
            "code": "SERVER_INTERNAL_ERROR",
            "message": "internal server error",
        },
    }


def test_unhandled_route_exception_returns_sanitized_500() -> None:
    class ExplodingHandler(
        GroundedAIHTTPHandler
    ):
        def handle(self, payload):
            raise RuntimeError(
                "sensitive database path C:/secret/provider-token"
            )

    handler = ExplodingHandler(
        application_service=SuccessService(),
    )
    app = create_grounded_ai_fastapi_app(
        handler=handler,
        authenticator=authenticator(),
    )

    client = TestClient(
        app,
        raise_server_exceptions=False,
    )
    response = client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "status": "ERROR",
        "error": {
            "category": "INTERNAL_ERROR",
            "code": "SERVER_INTERNAL_ERROR",
            "message": "internal server error",
        },
    }
    assert "sensitive" not in response.text
    assert "provider-token" not in response.text


def test_known_auth_failure_is_not_rewritten_to_500() -> None:
    app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
        ),
        authenticator=authenticator(),
    )

    response = TestClient(
        app,
        raise_server_exceptions=False,
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


def test_known_invalid_json_is_not_rewritten_to_500() -> None:
    app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
        ),
        authenticator=authenticator(),
    )

    response = TestClient(
        app,
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        headers={
            **headers(),
            "Content-Type": "application/json",
        },
        content=b"{bad-json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == (
        "SERVER_INVALID_JSON"
    )
