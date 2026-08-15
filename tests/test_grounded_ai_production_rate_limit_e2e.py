from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
)
from investment_terminal.api.http_handler import (
    GroundedAIHTTPHandler,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationResult,
    GroundedAIApplicationService,
)
from investment_terminal.server import production
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    RATE_LIMIT_CAPACITY_ENV,
    RATE_LIMIT_REFILL_PER_SECOND_ENV,
)


class DeterministicApplicationService(
    GroundedAIApplicationService
):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={
                "prompt": {
                    "request_id": request.request_id,
                },
                "answer": "grounded result",
            },
            trace={
                "request_id": request.request_id,
            },
        )


class DeterministicClock:
    value = Decimal("0")

    def __call__(self) -> Decimal:
        return type(self).value

    @classmethod
    def reset(cls) -> None:
        cls.value = Decimal("0")

    @classmethod
    def advance(cls, seconds: str) -> None:
        cls.value += Decimal(seconds)


def build_environment(
    *,
    database: Path,
) -> dict[str, str]:
    return {
        DATABASE_ENV: str(database),
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        DEFAULT_OPENAI_API_KEY_ENV: "provider-secret",
        DEFAULT_SERVER_API_KEY_ENV: "server-secret",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
        PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
        PROVIDER_BUDGET_CURRENCY_ENV: "USD",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "USD",
        RATE_LIMIT_CAPACITY_ENV: "1",
        RATE_LIMIT_REFILL_PER_SECOND_ENV: "0.5",
    }


def authenticated_headers() -> dict[str, str]:
    return {"X-API-Key": "server-secret"}


def payload(request_id: str) -> dict[str, str]:
    return {
        "request_id": request_id,
        "query": "Question",
    }


def build_client(
    *,
    monkeypatch,
    database: Path,
) -> TestClient:
    DeterministicClock.reset()

    monkeypatch.setattr(
        production,
        "GroundedAIServerMonotonicDecimalClock",
        DeterministicClock,
    )
    monkeypatch.setattr(
        production,
        "build_live_grounded_ai_http_handler",
        lambda **kwargs: GroundedAIHTTPHandler(
            application_service=(
                DeterministicApplicationService()
            )
        ),
    )

    app = production.create_app(
        build_environment(
            database=database,
        )
    )
    return TestClient(
        app,
        raise_server_exceptions=False,
    )


def test_production_rate_limit_runtime_e2e(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"sqlite-placeholder")
    client = build_client(
        monkeypatch=monkeypatch,
        database=database,
    )

    first = client.post(
        "/v1/grounded-ai",
        headers=authenticated_headers(),
        json=payload("request-1"),
    )

    assert first.status_code == 200
    assert first.headers["RateLimit-Limit"] == "1"
    assert first.headers["RateLimit-Remaining"] == "0"
    assert first.headers["RateLimit-Reset"] == "2"
    assert "Retry-After" not in first.headers

    throttled = client.post(
        "/v1/grounded-ai",
        headers=authenticated_headers(),
        json=payload("request-2"),
    )

    assert throttled.status_code == 429
    assert throttled.headers["Retry-After"] == "2"
    assert throttled.headers["RateLimit-Limit"] == "1"
    assert throttled.headers["RateLimit-Remaining"] == "0"
    assert throttled.headers["RateLimit-Reset"] == "2"
    assert throttled.json() == {
        "status": "ERROR",
        "error": {
            "category": "RATE_LIMITED",
            "code": "SERVER_RATE_LIMIT_EXCEEDED",
            "message": "request rate limit exceeded",
        },
    }

    DeterministicClock.advance("2")

    refilled = client.post(
        "/v1/grounded-ai",
        headers=authenticated_headers(),
        json=payload("request-3"),
    )

    assert refilled.status_code == 200
    assert refilled.headers["RateLimit-Limit"] == "1"
    assert refilled.headers["RateLimit-Remaining"] == "0"
    assert refilled.headers["RateLimit-Reset"] == "2"


def test_production_unauthenticated_request_does_not_consume_rate_limit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"sqlite-placeholder")
    client = build_client(
        monkeypatch=monkeypatch,
        database=database,
    )

    unauthenticated = client.post(
        "/v1/grounded-ai",
        json=payload("request-unauthenticated"),
    )

    assert unauthenticated.status_code == 401
    assert "RateLimit-Limit" not in unauthenticated.headers
    assert "RateLimit-Remaining" not in unauthenticated.headers
    assert "RateLimit-Reset" not in unauthenticated.headers

    authenticated = client.post(
        "/v1/grounded-ai",
        headers=authenticated_headers(),
        json=payload("request-authenticated"),
    )

    assert authenticated.status_code == 200
    assert authenticated.headers["RateLimit-Remaining"] == "0"


def test_production_openapi_exposes_rate_limit_client_contract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"sqlite-placeholder")
    client = build_client(
        monkeypatch=monkeypatch,
        database=database,
    )

    responses = client.get("/openapi.json").json()["paths"][
        "/v1/grounded-ai"
    ]["post"]["responses"]

    assert "RateLimit-Limit" in responses["200"]["headers"]
    assert "RateLimit-Remaining" in responses["200"]["headers"]
    assert "RateLimit-Reset" in responses["200"]["headers"]

    assert "Retry-After" in responses["429"]["headers"]
    assert "RateLimit-Limit" in responses["429"]["headers"]
    assert "RateLimit-Remaining" in responses["429"]["headers"]
    assert "RateLimit-Reset" in responses["429"]["headers"]

    assert "headers" not in responses["401"]
