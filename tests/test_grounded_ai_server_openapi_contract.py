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


def test_openapi_exposes_only_public_grounded_ai_surface() -> None:
    schema = app().openapi()

    assert set(schema["paths"]) == {
        "/v1/grounded-ai",
    }


def test_openapi_has_stable_operation_id_and_request_schema() -> None:
    operation = app().openapi()["paths"][
        "/v1/grounded-ai"
    ]["post"]

    assert operation["operationId"] == "grounded_ai_generate"

    schema = operation["requestBody"]["content"][
        "application/json"
    ]["schema"]

    assert schema["additionalProperties"] is False
    assert schema["required"] == [
        "request_id",
        "query",
    ]
    assert set(schema["properties"]) == {
        "request_id",
        "query",
        "subjects",
        "max_items",
    }


def test_openapi_documents_expected_status_surface() -> None:
    operation = app().openapi()["paths"][
        "/v1/grounded-ai"
    ]["post"]

    assert {
        "200",
        "400",
        "401",
        "403",
        "413",
        "500",
        "503",
    }.issubset(
        operation["responses"]
    )


def test_swagger_and_redoc_routes_are_disabled() -> None:
    client = TestClient(
        app(),
        raise_server_exceptions=False,
    )

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_openapi_json_remains_available() -> None:
    response = TestClient(
        app(),
        raise_server_exceptions=False,
    ).get("/openapi.json")

    assert response.status_code == 200
    assert "/v1/grounded-ai" in response.json()["paths"]


def test_schema_does_not_expose_internal_type_names_or_secret_values() -> None:
    schema_text = str(
        app().openapi()
    )

    forbidden = (
        "GroundedAIHTTPHandler",
        "GroundedAIServerAPIKeyAuthenticator",
        "GroundedAIServerRuntimeConfig",
        "OPENAI_API_KEY",
        "INVESTMENT_TERMINAL_SERVER_API_KEY",
        "server-secret",
    )

    for value in forbidden:
        assert value not in schema_text
