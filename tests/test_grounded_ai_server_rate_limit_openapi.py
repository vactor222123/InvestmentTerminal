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


class SuccessService(GroundedAIApplicationService):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={},
            trace={},
        )


def test_openapi_documents_rate_limit_response_headers() -> None:
    app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
        )
    )

    responses = app.openapi()["paths"][
        "/v1/grounded-ai"
    ]["post"]["responses"]

    for status_code in (
        "200",
        "400",
        "403",
        "413",
        "429",
        "503",
    ):
        headers = responses[status_code]["headers"]
        assert "RateLimit-Limit" in headers
        assert "RateLimit-Remaining" in headers
        assert "RateLimit-Reset" in headers

    assert "Retry-After" in responses["429"]["headers"]
    assert "headers" not in responses["401"]
    assert "headers" not in responses["500"]
