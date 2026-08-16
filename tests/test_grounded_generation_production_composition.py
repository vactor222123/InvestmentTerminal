import asyncio

from investment_terminal.ai.generation_recording import (
    GroundedGenerationRecordingService,
)
from investment_terminal.server import production
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    GROUNDED_GENERATION_DATABASE_ENV,
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


def test_production_composes_grounded_generation_persistence(
    monkeypatch,
    tmp_path,
) -> None:
    calls = {}

    class FakeApp:
        pass

    monkeypatch.setattr(
        production,
        "build_live_grounded_ai_http_handler",
        lambda **kwargs: (
            calls.setdefault("handler_kwargs", kwargs)
            or object()
        ),
    )

    def fake_factory(**kwargs):
        calls["lifespan"] = kwargs["lifespan"]
        return FakeApp()

    monkeypatch.setattr(
        production,
        "create_grounded_ai_fastapi_app",
        fake_factory,
    )

    knowledge = tmp_path / "knowledge.db"
    generation_database = tmp_path / "generations.db"

    values = {
        DATABASE_ENV: str(knowledge),
        USAGE_COST_LEDGER_DATABASE_ENV: str(
            tmp_path / "provider_usage_cost.db"
        ),
        GROUNDED_GENERATION_DATABASE_ENV: str(
            generation_database
        ),
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        DEFAULT_SERVER_API_KEY_ENV: "server-secret",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
        PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
        PROVIDER_BUDGET_CURRENCY_ENV: "EUR",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "EUR",
    }

    app = production.create_app(values)

    assert not generation_database.exists()

    async def enter_lifespan() -> None:
        async with calls["lifespan"](app):
            assert generation_database.is_file()

    asyncio.run(
        enter_lifespan()
    )

    recorder = calls["handler_kwargs"][
        "generation_recording_service"
    ]
    assert isinstance(
        recorder,
        GroundedGenerationRecordingService,
    )
