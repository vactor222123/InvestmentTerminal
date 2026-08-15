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
from investment_terminal.server.fastapi_app import (
    create_grounded_ai_fastapi_app,
)
from investment_terminal.server.readiness import (
    GroundedAIServerReadinessService,
)
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    GroundedAIServerRuntimeConfig,
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


def handler():
    return GroundedAIHTTPHandler(
        application_service=SuccessService(),
    )


def readiness(
    database: Path,
    *,
    secret: str | None,
):
    ledger_database = database.with_name(
        "provider_usage_cost.db"
    )
    ledger_database.write_bytes(b"")

    config = GroundedAIServerRuntimeConfig.from_environment(
        {
            DATABASE_ENV: str(database),
            USAGE_COST_LEDGER_DATABASE_ENV: str(
                ledger_database
            ),
            MODEL_ENV: "gpt-test",
            ALLOWED_MODELS_ENV: "gpt-test",
            PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
            PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
            PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
            PROVIDER_BUDGET_CURRENCY_ENV: "USD",
            PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
            PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
            PROVIDER_PRICING_CURRENCY_ENV: "USD",
        }
    )
    environment = {}
    if secret is not None:
        environment[
            DEFAULT_OPENAI_API_KEY_ENV
        ] = secret

    return GroundedAIServerReadinessService(
        config=config,
        environment=environment,
    )


def test_health_is_always_lightweight_200() -> None:
    client = TestClient(
        create_grounded_ai_fastapi_app(
            handler=handler(),
        )
    )

    response = client.get(
        "/health"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "OK",
    }


def test_ready_returns_200_when_local_prerequisites_are_ready(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")

    client = TestClient(
        create_grounded_ai_fastapi_app(
            handler=handler(),
            readiness_service=readiness(
                database,
                secret="secret",
            ),
        )
    )

    response = client.get(
        "/ready"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "READY"


def test_ready_returns_503_when_credentials_are_missing(
    tmp_path: Path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")

    client = TestClient(
        create_grounded_ai_fastapi_app(
            handler=handler(),
            readiness_service=readiness(
                database,
                secret=None,
            ),
        )
    )

    response = client.get(
        "/ready"
    )

    assert response.status_code == 503
    assert response.json()["status"] == "NOT_READY"


def test_ready_without_service_fails_closed() -> None:
    client = TestClient(
        create_grounded_ai_fastapi_app(
            handler=handler(),
        )
    )

    response = client.get(
        "/ready"
    )

    assert response.status_code == 503
    assert response.json() == {
        "status": "NOT_READY",
        "checks": {},
    }
