from pathlib import Path

from fastapi.testclient import TestClient

from investment_terminal.api.http_handler import GroundedAIHTTPHandler
from investment_terminal.application.grounded_ai import GroundedAIApplicationResult, GroundedAIApplicationService
from investment_terminal.server import production
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV, DATABASE_ENV, USAGE_COST_LEDGER_DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV, MAX_REQUEST_BODY_BYTES_ENV, MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV, PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV, PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV, PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
)
from investment_terminal.ai.providers.composition import DEFAULT_OPENAI_API_KEY_ENV


class DeterministicApplicationService(GroundedAIApplicationService):
    def execute(self, request):
        return GroundedAIApplicationResult(
            generation={"prompt": {"request_id": request.request_id}, "answer": "grounded result"},
            trace={"request_id": request.request_id, "subject_keys": list(request.subject_keys)},
        )


def build_environment(*, database: Path) -> dict[str, str]:
    return {
        DATABASE_ENV: str(database),
        USAGE_COST_LEDGER_DATABASE_ENV: str(database.with_name("provider_usage_cost.db")),
        MODEL_ENV: "gpt-test", ALLOWED_MODELS_ENV: "gpt-test",
        DEFAULT_OPENAI_API_KEY_ENV: "provider-secret",
        DEFAULT_SERVER_API_KEY_ENV: "server-secret",
        MAX_REQUEST_BODY_BYTES_ENV: "256",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32", PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50", PROVIDER_BUDGET_CURRENCY_ENV: "USD",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "USD",
    }


def test_production_server_runtime_e2e(monkeypatch, tmp_path: Path) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"sqlite-placeholder")
    monkeypatch.setattr(
        production, "build_live_grounded_ai_http_handler",
        lambda **kwargs: GroundedAIHTTPHandler(application_service=DeterministicApplicationService()),
    )
    app = production.create_app(build_environment(database=database))
    client = TestClient(app, raise_server_exceptions=False)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "OK"}
    assert health.headers["X-Content-Type-Options"] == "nosniff"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "READY",
        "checks": {
            "knowledge_database": "READY",
            "provider_usage_cost_database": "READY",
            "grounded_generation_database": "READY",
            "provider_credentials": "READY",
        },
    }

    unauthenticated = client.post("/v1/grounded-ai", json={"request_id": "request-1", "query": "Question"})
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "SERVER_AUTHENTICATION_REQUIRED"

    success = client.post(
        "/v1/grounded-ai",
        headers={"X-API-Key": "server-secret"},
        json={"request_id": "request-1", "query": "Question", "subjects": ["WORLD"]},
    )
    assert success.status_code == 200
    assert success.json() == {
        "status": "SUCCESS", "request_id": "request-1",
        "data": {
            "generation": {"prompt": {"request_id": "request-1"}, "answer": "grounded result"},
            "trace": {"request_id": "request-1", "subject_keys": ["WORLD"]},
        },
    }
    assert success.headers["Cache-Control"] == "no-store"

    recent = client.get(
        "/v1/grounded-generations",
        params={"limit": 10},
        headers={"X-API-Key": "server-secret"},
    )
    assert recent.status_code == 200
    assert recent.json()["data"] == {
        "count": 0,
        "records": [],
    }

    generation_unauthenticated = client.get(
        "/v1/grounded-generations",
        params={"limit": 10},
    )
    assert generation_unauthenticated.status_code == 401

    oversized = client.post(
        "/v1/grounded-ai", headers={"X-API-Key": "server-secret"},
        json={"request_id": "request-2", "query": "x" * 400},
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "SERVER_REQUEST_BODY_TOO_LARGE"

    invalid_json = client.post(
        "/v1/grounded-ai",
        headers={"X-API-Key": "server-secret", "Content-Type": "application/json"},
        content=b"{bad-json",
    )
    assert invalid_json.status_code == 400
    assert invalid_json.json()["error"]["code"] == "SERVER_INVALID_JSON"

    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert set(schema.json()["paths"]) == {
        "/v1/grounded-ai",
        "/v1/grounded-generations",
        "/v1/grounded-generations/{request_id}",
    }
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_production_server_runtime_e2e_readiness_fails_closed(monkeypatch, tmp_path: Path) -> None:
    database = tmp_path / "missing.db"
    monkeypatch.setattr(
        production, "build_live_grounded_ai_http_handler",
        lambda **kwargs: GroundedAIHTTPHandler(application_service=DeterministicApplicationService()),
    )
    environment = build_environment(database=database)
    del environment[DEFAULT_OPENAI_API_KEY_ENV]
    app = production.create_app(environment)
    response = TestClient(app, raise_server_exceptions=False).get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "NOT_READY",
        "checks": {
            "knowledge_database": "NOT_READY",
            "provider_usage_cost_database": "READY",
            "grounded_generation_database": "READY",
            "provider_credentials": "NOT_READY",
        },
    }
