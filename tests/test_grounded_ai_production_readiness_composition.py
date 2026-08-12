from investment_terminal.server import production
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
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
    ):
        calls["handler"] = handler
        calls["readiness_service"] = readiness_service
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
        }
    )

    assert isinstance(
        app,
        FakeApp,
    )
    assert isinstance(
        calls["handler"],
        FakeHandler,
    )
    assert (
        calls["readiness_service"]
        is not None
    )
