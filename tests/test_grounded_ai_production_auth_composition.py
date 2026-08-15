import pytest

from investment_terminal.application.grounded_generation_history import (
    GroundedGenerationHistoryService,
)
from investment_terminal.server import production
from investment_terminal.server.rate_limit_admission import (
    GroundedAIServerRateLimitAdmissionService,
)
from investment_terminal.server.rate_limit_identity import (
    GroundedAIServerRateLimitIdentityDeriver,
)
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
)


def environment(
    tmp_path,
):
    return {
        DATABASE_ENV: str(
            tmp_path / "knowledge.db"
        ),
        USAGE_COST_LEDGER_DATABASE_ENV: str(
            tmp_path / "provider_usage_cost.db"
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


def test_production_requires_server_api_key_before_app_creation(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        production,
        "build_live_grounded_ai_http_handler",
        lambda **kwargs: object(),
    )

    with pytest.raises(
        ValueError,
        match="required server API key environment variable",
    ):
        production.create_app(
            environment(tmp_path)
        )


def test_production_wires_authenticator(
    monkeypatch,
    tmp_path,
) -> None:
    calls = {}

    class FakeHandler:
        pass

    class FakeApp:
        pass

    monkeypatch.setattr(
        production,
        "build_live_grounded_ai_http_handler",
        lambda **kwargs: FakeHandler(),
    )

    def fake_factory(
        *,
        handler,
        readiness_service,
        authenticator,
        request_limit_policy,
        rate_limit_admission_service,
        rate_limit_identity_deriver,
        grounded_generation_history_service,
    ):
        calls["handler"] = handler
        calls["readiness_service"] = readiness_service
        calls["authenticator"] = authenticator
        calls["request_limit_policy"] = request_limit_policy
        calls["rate_limit_admission_service"] = rate_limit_admission_service
        calls["rate_limit_identity_deriver"] = rate_limit_identity_deriver
        calls["grounded_generation_history_service"] = (
            grounded_generation_history_service
        )
        return FakeApp()

    monkeypatch.setattr(
        production,
        "create_grounded_ai_fastapi_app",
        fake_factory,
    )

    values = environment(tmp_path)
    values[DEFAULT_SERVER_API_KEY_ENV] = "server-secret"

    app = production.create_app(values)

    assert isinstance(app, FakeApp)
    assert calls["authenticator"].authenticate("server-secret")
    assert calls["request_limit_policy"].max_body_bytes == 65536
    assert isinstance(
        calls["rate_limit_admission_service"],
        GroundedAIServerRateLimitAdmissionService,
    )
    assert isinstance(
        calls["rate_limit_identity_deriver"],
        GroundedAIServerRateLimitIdentityDeriver,
    )
    assert isinstance(
        calls["grounded_generation_history_service"],
        GroundedGenerationHistoryService,
    )
