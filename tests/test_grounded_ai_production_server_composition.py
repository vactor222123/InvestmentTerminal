from decimal import Decimal

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


def test_production_factory_routes_config_through_api_composition(
    monkeypatch,
    tmp_path,
):
    calls = {}

    class FakeHandler:
        pass

    class FakeApp:
        pass

    def fake_build_handler(**kwargs):
        calls["handler_kwargs"] = kwargs
        return FakeHandler()

    def fake_fastapi_factory(
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
        "build_live_grounded_ai_http_handler",
        fake_build_handler,
    )
    monkeypatch.setattr(
        production,
        "create_grounded_ai_fastapi_app",
        fake_fastapi_factory,
    )

    app = production.create_app({
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
    })

    assert isinstance(app, FakeApp)
    assert isinstance(calls["handler"], FakeHandler)
    assert calls["readiness_service"] is not None
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

    handler_kwargs = calls["handler_kwargs"]
    assert handler_kwargs["model_identity"] == "gpt-test"
    assert handler_kwargs["timeout_seconds"] == 30
    assert handler_kwargs["max_retries"] == 2
    assert handler_kwargs["requested_max_output_tokens"] == 32
    assert handler_kwargs["governance_policy"].assess(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    ).allowed

    pricing = handler_kwargs["pricing_policy"].require_entry(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    )
    assert pricing.input_cost_per_million_tokens == Decimal("0.10")
    assert pricing.output_cost_per_million_tokens == Decimal("0.20")
    assert pricing.currency == "USD"

    budget = handler_kwargs["budget_policy"]
    assert budget.max_output_tokens == 32
    assert budget.max_total_tokens == 128
    assert budget.max_total_cost == Decimal("1.50")
    assert budget.currency == "USD"


def test_production_module_has_no_import_time_app_construction():
    assert not hasattr(production, "app")
