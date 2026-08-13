from investment_terminal.server import production
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    MODEL_ENV,
    RATE_LIMIT_CAPACITY_ENV,
    RATE_LIMIT_REFILL_PER_SECOND_ENV,
)


def test_production_wires_rate_limit_services(
    monkeypatch,
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

    def fake_factory(**kwargs):
        calls.update(kwargs)
        return FakeApp()

    monkeypatch.setattr(
        production,
        "create_grounded_ai_fastapi_app",
        fake_factory,
    )

    values = {
        DATABASE_ENV: "data/knowledge/knowledge.db",
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        DEFAULT_SERVER_API_KEY_ENV: "server-secret",
        RATE_LIMIT_CAPACITY_ENV: "3",
        RATE_LIMIT_REFILL_PER_SECOND_ENV: "0.25",
    }

    app = production.create_app(
        values
    )

    assert isinstance(
        app,
        FakeApp,
    )
    assert (
        calls["rate_limit_admission_service"]
        is not None
    )
    assert (
        calls["rate_limit_identity_deriver"]
        is not None
    )

    identity = calls[
        "rate_limit_identity_deriver"
    ].derive(
        "server-secret"
    )

    assert calls[
        "rate_limit_admission_service"
    ].decide(
        identity=identity
    ).allowed
