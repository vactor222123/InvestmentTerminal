from fastapi.testclient import TestClient

from investment_terminal.api.http_handler import GroundedAIHTTPHandler
from investment_terminal.application.errors import GroundedAIApplicationError
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


class SuccessService(GroundedAIApplicationService):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={"prompt": {"request_id": request.request_id}},
            trace={"request_id": request.request_id},
        )


class PolicyDeniedService(GroundedAIApplicationService):
    def execute(self, request):
        raise GroundedAIApplicationError(
            category="POLICY_DENIED",
            code="APPLICATION_POLICY_DENIED",
            message="denied",
        )


def client_for(service: GroundedAIApplicationService) -> TestClient:
    app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=service
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret",
        ),
    )
    return TestClient(app)


def auth_headers() -> dict[str, str]:
    return {
        "X-API-Key": "server-secret",
    }


def test_fastapi_runtime_routes_success_without_domain_remapping() -> None:
    response = client_for(
        SuccessService()
    ).post(
        "/v1/grounded-ai",
        headers=auth_headers(),
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["request_id"] == "request-1"


def test_fastapi_runtime_preserves_policy_denial_status_and_body() -> None:
    response = client_for(
        PolicyDeniedService()
    ).post(
        "/v1/grounded-ai",
        headers=auth_headers(),
        json={
            "request_id": "request-1",
            "query": "Question",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == (
        "APPLICATION_POLICY_DENIED"
    )


def test_fastapi_runtime_delegates_invalid_decoded_payload_to_handler() -> None:
    response = client_for(
        SuccessService()
    ).post(
        "/v1/grounded-ai",
        headers=auth_headers(),
        json={
            "request_id": "request-1",
            "query": "Question",
            "unexpected": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == (
        "API_INVALID_REQUEST"
    )


def test_fastapi_runtime_delegates_non_object_json_to_handler() -> None:
    response = client_for(
        SuccessService()
    ).post(
        "/v1/grounded-ai",
        headers=auth_headers(),
        json=[
            "not",
            "an",
            "object",
        ],
    )

    assert response.status_code == 400
    assert response.json()["request_id"] == "UNKNOWN"


def test_fastapi_app_exposes_grounded_ai_route() -> None:
    app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret",
        ),
    )

    paths = {
        route.path
        for route in app.routes
    }

    assert "/v1/grounded-ai" in paths
