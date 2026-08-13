from fastapi.testclient import TestClient

from investment_terminal.api.http_handler import GroundedAIHTTPHandler
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
from investment_terminal.server.security_headers import (
    SECURITY_HEADERS,
)


class SuccessService(GroundedAIApplicationService):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={},
            trace={},
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


def assert_security_headers(response) -> None:
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_security_headers_are_applied_to_health_success() -> None:
    response = TestClient(
        app(),
        raise_server_exceptions=False,
    ).get("/health")
    assert response.status_code == 200
    assert_security_headers(response)


def test_security_headers_are_applied_to_auth_failure() -> None:
    response = TestClient(
        app(),
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )
    assert response.status_code == 401
    assert_security_headers(response)


def test_security_headers_are_applied_to_invalid_json() -> None:
    response = TestClient(
        app(),
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        headers={
            "X-API-Key": "server-secret",
            "Content-Type": "application/json",
        },
        content=b"{bad-json",
    )
    assert response.status_code == 400
    assert_security_headers(response)


def test_hsts_is_not_assumed_by_application_runtime() -> None:
    response = TestClient(
        app(),
        raise_server_exceptions=False,
    ).get("/health")
    assert "strict-transport-security" not in response.headers
