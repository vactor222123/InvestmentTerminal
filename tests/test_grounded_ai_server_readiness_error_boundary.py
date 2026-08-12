from fastapi.testclient import TestClient

from investment_terminal.api.http_handler import (
    GroundedAIHTTPHandler,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)
from investment_terminal.server.fastapi_app import (
    create_grounded_ai_fastapi_app,
)
from investment_terminal.server.readiness import (
    GroundedAIServerReadinessService,
)


class SuccessService(
    GroundedAIApplicationService
):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={},
            trace={},
        )


class ExplodingReadiness(
    GroundedAIServerReadinessService
):
    def check(self):
        raise RuntimeError(
            "secret readiness failure detail"
        )


def test_unhandled_readiness_exception_is_sanitized() -> None:
    readiness = object.__new__(
        ExplodingReadiness
    )

    app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
        ),
        readiness_service=readiness,
    )

    response = TestClient(
        app,
        raise_server_exceptions=False,
    ).get(
        "/ready"
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == (
        "SERVER_INTERNAL_ERROR"
    )
    assert "secret readiness failure detail" not in response.text
