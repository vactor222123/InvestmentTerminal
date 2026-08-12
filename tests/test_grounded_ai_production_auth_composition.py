import pytest

from investment_terminal.server import production
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    MODEL_ENV,
)


def environment():
    return {
        DATABASE_ENV: "data/knowledge/knowledge.db",
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
    }


def test_production_requires_server_api_key_before_app_creation(
    monkeypatch,
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
            environment()
        )


def test_production_wires_authenticator(
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

    def fake_factory(
        *,
        handler,
        readiness_service,
        authenticator,
        request_limit_policy,
    ):
        calls["handler"] = handler
        calls["readiness_service"] = readiness_service
        calls["authenticator"] = authenticator
        calls["request_limit_policy"] = request_limit_policy
        return FakeApp()

    monkeypatch.setattr(
        production,
        "create_grounded_ai_fastapi_app",
        fake_factory,
    )

    values = environment()
    values[
        DEFAULT_SERVER_API_KEY_ENV
    ] = "server-secret"

    app = production.create_app(
        values
    )

    assert isinstance(app, FakeApp)
    assert calls["authenticator"].authenticate(
        "server-secret"
    )
    assert calls["request_limit_policy"].max_body_bytes == 65536
