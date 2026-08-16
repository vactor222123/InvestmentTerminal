import asyncio

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


def test_production_factory_wires_readiness_service(
    monkeypatch,
    tmp_path,
) -> None:
    database = tmp_path / "knowledge.db"
    database.write_bytes(b"")

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
        lifespan,
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
        calls["lifespan"] = lifespan
        return FakeApp()

    monkeypatch.setattr(
        production,
        "create_grounded_ai_fastapi_app",
        fake_factory,
    )

    app = production.create_app(
        {
            DATABASE_ENV: str(database),
            USAGE_COST_LEDGER_DATABASE_ENV: str(
                database.with_name("provider_usage_cost.db")
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
    )

    assert isinstance(app, FakeApp)
    assert isinstance(calls["handler"], FakeHandler)
    assert calls["readiness_service"] is not None

    ledger = database.with_name(
        "provider_usage_cost.db"
    )
    assert not ledger.exists()

    async def enter_lifespan() -> None:
        async with calls["lifespan"](app):
            assert ledger.is_file()
            assert calls["readiness_service"].check().checks[
                "provider_usage_cost_database"
            ] == "READY"

    asyncio.run(
        enter_lifespan()
    )

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
