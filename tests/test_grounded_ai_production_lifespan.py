from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from investment_terminal.api.http_handler import GroundedAIHTTPHandler
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
    USAGE_COST_LEDGER_DATABASE_ENV,
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


def environment(
    tmp_path: Path,
) -> dict[str, str]:
    return {
        DATABASE_ENV: str(
            tmp_path / "knowledge.db"
        ),
        USAGE_COST_LEDGER_DATABASE_ENV: str(
            tmp_path / "provider_usage_cost.db"
        ),
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        DEFAULT_SERVER_API_KEY_ENV: "server-secret",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
        PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
        PROVIDER_BUDGET_CURRENCY_ENV: "USD",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "USD",
    }


def install_fake_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        production,
        "build_live_grounded_ai_http_handler",
        lambda **kwargs: GroundedAIHTTPHandler(
            application_service=(
                DeterministicApplicationService()
            )
        ),
    )


def test_create_app_does_not_initialize_operational_databases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_fake_handler(
        monkeypatch
    )
    env = environment(
        tmp_path
    )

    app = production.create_app(
        env
    )

    assert app is not None
    assert not Path(
        env[USAGE_COST_LEDGER_DATABASE_ENV]
    ).exists()
    assert not Path(
        env[USAGE_COST_LEDGER_DATABASE_ENV]
    ).with_name(
        "grounded_generations.db"
    ).exists()


def test_lifespan_initializes_operational_databases_before_requests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_fake_handler(
        monkeypatch
    )
    env = environment(
        tmp_path
    )

    app = production.create_app(
        env
    )
    ledger = Path(
        env[USAGE_COST_LEDGER_DATABASE_ENV]
    )
    generations = ledger.with_name(
        "grounded_generations.db"
    )

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as client:
        assert ledger.is_file()
        assert generations.is_file()

        response = client.get(
            "/ready"
        )
        assert response.status_code == 503
        assert response.json()["checks"][
            "provider_usage_cost_database"
        ] == "READY"
        assert response.json()["checks"][
            "grounded_generation_database"
        ] == "READY"
        assert response.json()["checks"][
            "knowledge_database"
        ] == "NOT_READY"


def test_lifespan_startup_failure_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_fake_handler(
        monkeypatch
    )
    env = environment(
        tmp_path
    )

    def fail_initialize(self):
        raise OSError(
            "simulated startup failure"
        )

    monkeypatch.setattr(
        production.GroundedProviderUsageCostLedgerSQLiteStore,
        "initialize",
        fail_initialize,
    )

    app = production.create_app(
        env
    )

    with pytest.raises(
        OSError,
        match="simulated startup failure",
    ):
        with TestClient(
            app
        ):
            pass


def test_repeated_app_construction_has_no_runtime_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_fake_handler(
        monkeypatch
    )
    env = environment(
        tmp_path
    )

    first = production.create_app(
        env
    )
    second = production.create_app(
        env
    )

    assert first is not second
    assert not Path(
        env[USAGE_COST_LEDGER_DATABASE_ENV]
    ).exists()
