from investment_terminal.server import production
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    MODEL_ENV,
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

    app = production.create_app(
        {
            DATABASE_ENV: str(database),
            MODEL_ENV: "gpt-test",
            ALLOWED_MODELS_ENV: "gpt-test",
            DEFAULT_SERVER_API_KEY_ENV: "server-secret",
        }
    )

    assert isinstance(app, FakeApp)
    assert isinstance(calls["handler"], FakeHandler)
    assert calls["readiness_service"] is not None
    assert calls["authenticator"].authenticate("server-secret")
    assert calls["request_limit_policy"].max_body_bytes == 65536
