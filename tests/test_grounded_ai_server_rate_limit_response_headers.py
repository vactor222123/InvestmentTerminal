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


def app_for(
    *,
    clock: Clock,
    capacity: int = 2,
    refill: str = "0.5",
):
    admission = GroundedAIServerRateLimitAdmissionService(
        policy=GroundedAIServerRateLimitPolicy(
            capacity=capacity,
            refill_tokens_per_second=Decimal(refill),
        ),
        clock=clock,
    )
    return create_grounded_ai_fastapi_app(
        handler=GroundedAIHTTPHandler(
            application_service=SuccessService(),
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


def test_allowed_response_exposes_rate_limit_metadata() -> None:
    response = TestClient(
        app_for(clock=Clock()),
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    )

    assert response.status_code == 200
    assert response.headers["RateLimit-Limit"] == "2"
    assert response.headers["RateLimit-Remaining"] == "1"
    assert response.headers["RateLimit-Reset"] == "2"
    assert "Retry-After" not in response.headers


def test_denied_response_keeps_retry_after_and_rate_limit_metadata() -> None:
    client = TestClient(
        app_for(
            clock=Clock(),
            capacity=1,
        ),
        raise_server_exceptions=False,
    )

    assert client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    ).status_code == 200

    response = client.post(
        "/v1/grounded-ai",
        headers=headers(),
        json=payload(),
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "2"
    assert response.headers["RateLimit-Limit"] == "1"
    assert response.headers["RateLimit-Remaining"] == "0"
    assert response.headers["RateLimit-Reset"] == "2"


def test_admitted_invalid_request_keeps_rate_limit_metadata() -> None:
    response = TestClient(
        app_for(clock=Clock()),
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        headers=headers(),
        content=b"not-json",
    )

    assert response.status_code == 400
    assert response.headers["RateLimit-Limit"] == "2"
    assert response.headers["RateLimit-Remaining"] == "1"
    assert response.headers["RateLimit-Reset"] == "2"


def test_unauthenticated_response_exposes_no_rate_limit_metadata() -> None:
    response = TestClient(
        app_for(clock=Clock()),
        raise_server_exceptions=False,
    ).post(
        "/v1/grounded-ai",
        json=payload(),
    )

    assert response.status_code == 401
    assert "RateLimit-Limit" not in response.headers
    assert "RateLimit-Remaining" not in response.headers
    assert "RateLimit-Reset" not in response.headers
    assert "Retry-After" not in response.headers
