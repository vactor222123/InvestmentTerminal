from decimal import Decimal

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
from investment_terminal.server.rate_limit_admission import (
    GroundedAIServerRateLimitAdmissionService,
)
from investment_terminal.server.rate_limit_identity import (
    GroundedAIServerRateLimitIdentityDeriver,
)
from investment_terminal.server.rate_limits import (
    GroundedAIServerRateLimitPolicy,
)


class Clock:
    def __init__(self) -> None:
        self.value = Decimal("0")

    def __call__(self) -> Decimal:
        return self.value

    def advance(self, seconds: str) -> None:
        self.value += Decimal(seconds)


class SuccessService(GroundedAIApplicationService):
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


class NeverCallService(GroundedAIApplicationService):
    def execute(self, request):
        raise AssertionError(
            "application must not execute for throttled requests"
        )


def app_for(
    *,
    clock: Clock,
    service,
):
    admission = GroundedAIServerRateLimitAdmissionService(
        policy=GroundedAIServerRateLimitPolicy(
            capacity=1,
            refill_tokens_per_second=Decimal("0.5"),
        ),
        clock=clock,
    )
    return create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=service,
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret",
        ),
        rate_limit_admission_service=admission,
        rate_limit_identity_deriver=(
            GroundedAIServerRateLimitIdentityDeriver()
        ),
    )


def headers():
    return {
        "X-API-Key": "server-secret",
    }


def payload():
    return {
        "request_id": "request-1",
        "query": "Question",
    }


def test_second_authenticated_request_is_rate_limited_with_retry_after() -> None:
    clock = Clock()
    client = TestClient(
        app_for(
            clock=clock,
            service=SuccessService(),
        ),
        raise_server_exceptions=False,
    )

    first = client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    )
    second = client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "2"
    assert second.json() == {
        "status": "ERROR",
        "error": {
            "category": "RATE_LIMITED",
            "code": "SERVER_RATE_LIMIT_EXCEEDED",
            "message": "request rate limit exceeded",
        },
    }


def test_rate_limit_precedes_body_read_and_application_execution() -> None:
    clock = Clock()

    # Consume the single token using a successful app.
    shared_admission = GroundedAIServerRateLimitAdmissionService(
        policy=GroundedAIServerRateLimitPolicy(
            capacity=1,
            refill_tokens_per_second=Decimal("1"),
        ),
        clock=clock,
    )
    deriver = GroundedAIServerRateLimitIdentityDeriver()

    first_app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret",
        ),
        rate_limit_admission_service=shared_admission,
        rate_limit_identity_deriver=deriver,
    )
    TestClient(first_app).post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    )

    throttled_app = create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=NeverCallService(),
        ),
        authenticator=GroundedAIServerAPIKeyAuthenticator(
            expected_api_key="server-secret",
        ),
        rate_limit_admission_service=shared_admission,
        rate_limit_identity_deriver=deriver,
    )
    response = TestClient(
        throttled_app,
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        headers=headers(),
        content=b"x" * 100000,
    )

    assert response.status_code == 429


def test_unauthenticated_request_preserves_401_precedence() -> None:
    clock = Clock()
    response = TestClient(
        app_for(
            clock=clock,
            service=NeverCallService(),
        ),
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        json=payload(),
    )

    assert response.status_code == 401


def test_request_is_allowed_again_after_refill() -> None:
    clock = Clock()
    client = TestClient(
        app_for(
            clock=clock,
            service=SuccessService(),
        ),
        raise_server_exceptions=False,
    )

    assert client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    ).status_code == 200

    assert client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    ).status_code == 429

    clock.advance("2")

    assert client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    ).status_code == 200
